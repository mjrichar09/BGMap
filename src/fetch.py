"""Stage 2: fetch game details from the BGG XML API2, slowly, with a cache.

Reads data/ids.csv, requests `thing?id=...&stats=1` in batches of 20 and saves
every raw response to data/raw/. A manifest records which IDs each file
covers, so an interrupted run resumes where it stopped. IDs that BGG doesn't
return are logged and retried with --retry-missing.

    export BGG_TOKEN=...          # or put it in .env
    python src/fetch.py --limit 40   # smoke test: two requests
    python src/fetch.py              # full run, ~1-2 hours
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from lxml import etree

from common import BGG_API, IDS_CSV, RAW_DIR, load_dotenv

BATCH_SIZE = 20  # BGG's per-request cap for `thing`
MANIFEST = RAW_DIR / "manifest.jsonl"
USER_AGENT = "bgmap/0.1 (personal non-commercial research project)"


class FatalFetchError(RuntimeError):
    pass


def read_manifest(path: Path = MANIFEST) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def plan_batches(all_ids: list[int], manifest: list[dict], retry_missing: bool) -> list[list[int]]:
    """IDs not yet covered by any cached file, in their original order, chunked."""
    returned = {i for entry in manifest for i in entry["returned"]}
    requested = {i for entry in manifest for i in entry["requested"]}
    done = returned if retry_missing else requested
    todo = [i for i in all_ids if i not in done]
    return [todo[k : k + BATCH_SIZE] for k in range(0, len(todo), BATCH_SIZE)]


def returned_ids(xml_bytes: bytes) -> list[int]:
    root = etree.fromstring(xml_bytes)
    if root.tag != "items":
        raise ValueError(f"unexpected root <{root.tag}>")
    return [int(item.get("id")) for item in root.iterfind("item")]


def get_batch(session: requests.Session, ids: list[int], max_tries: int = 6) -> bytes:
    """One `thing` request, retrying BGG's queue (202), throttling (429) and 5xx."""
    params = {"id": ",".join(map(str, ids)), "stats": 1}
    wait = 5.0
    for attempt in range(1, max_tries + 1):
        try:
            resp = session.get(f"{BGG_API}/thing", params=params, timeout=60)
        except requests.RequestException as exc:
            print(f"  network error ({exc}); retry {attempt}/{max_tries} in {wait:.0f}s", file=sys.stderr)
        else:
            if resp.status_code == 200:
                return resp.content
            if resp.status_code in (401, 403):
                raise FatalFetchError(
                    f"HTTP {resp.status_code}: token missing or rejected. Check BGG_TOKEN and that "
                    "your application is approved. Response: " + resp.text[:200]
                )
            retry_after = resp.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait = max(wait, float(retry_after))
            print(f"  HTTP {resp.status_code}; retry {attempt}/{max_tries} in {wait:.0f}s", file=sys.stderr)
        time.sleep(wait)
        wait = min(wait * 2, 300)
    raise RuntimeError(f"gave up on batch starting {ids[0]} after {max_tries} tries")


def save_batch(xml_bytes: bytes, ids: list[int], got: list[int]) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    n = len(list(RAW_DIR.glob("batch_*.xml")))
    path = RAW_DIR / f"batch_{n:05d}.xml"
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(xml_bytes)
    tmp.replace(path)
    entry = {"file": path.name, "requested": ids, "returned": got, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with MANIFEST.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return path


def make_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT})
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delay", type=float, default=5.0, help="seconds between requests (default 5)")
    ap.add_argument("--limit", type=int, help="only fetch the first N not-yet-cached IDs")
    ap.add_argument("--retry-missing", action="store_true", help="re-request IDs BGG didn't return before")
    args = ap.parse_args()

    load_dotenv()
    token = os.environ.get("BGG_TOKEN")
    if not token:
        sys.exit("BGG_TOKEN is not set (see .env.example).")
    if not IDS_CSV.exists():
        sys.exit(f"{IDS_CSV} not found; run src/ids.py first.")

    all_ids = pd.read_csv(IDS_CSV)["id"].astype(int).tolist()
    batches = plan_batches(all_ids, read_manifest(), args.retry_missing)
    if args.limit:
        flat = [i for b in batches for i in b][: args.limit]
        batches = [flat[k : k + BATCH_SIZE] for k in range(0, len(flat), BATCH_SIZE)]
    total = sum(map(len, batches))
    print(f"{len(all_ids):,} IDs, {total:,} to fetch in {len(batches):,} requests "
          f"(~{len(batches) * args.delay / 60:.0f} min at {args.delay}s apart)")

    session = make_session(token)
    missing_total = 0
    for k, ids in enumerate(batches, 1):
        try:
            xml_bytes = get_batch(session, ids)
            got = returned_ids(xml_bytes)
        except FatalFetchError as exc:
            sys.exit(str(exc))
        except (RuntimeError, ValueError, etree.XMLSyntaxError) as exc:
            # Not cached, so the next run picks this batch up again.
            print(f"[{k}/{len(batches)}] FAILED {ids[0]}..: {exc}", file=sys.stderr)
            time.sleep(args.delay)
            continue
        path = save_batch(xml_bytes, ids, got)
        missing = sorted(set(ids) - set(got))
        missing_total += len(missing)
        note = f", missing {missing}" if missing else ""
        print(f"[{k}/{len(batches)}] {len(got)}/{len(ids)} games -> {path.name}{note}")
        time.sleep(args.delay)

    if missing_total:
        print(f"{missing_total} IDs were not returned; rerun with --retry-missing to try them again.")


if __name__ == "__main__":
    main()
