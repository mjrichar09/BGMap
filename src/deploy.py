"""Deploy a domain's exported site (data/<domain>/site) to its Vercel project's production.

Production is public, so this refuses any build whose ratings aren't TMDB's:
IMDb's datasets may not be republished. Run src.export first.

    python -m src.deploy --domain movies
"""

import argparse
import json
import shutil
import subprocess

from src.common import domain_dir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, choices=["movies"])
    args = ap.parse_args()

    site = domain_dir(args.domain) / "site"
    manifest = json.loads((site / "data" / "manifest.json").read_text(encoding="utf-8"))
    source = manifest.get("ratings", {}).get("source")
    if source != "TMDB":
        raise SystemExit(f"{site} has {source} ratings; only a TMDB build may be published. Rerun src.export without --private.")
    if not (site / ".vercel" / "project.json").exists():
        raise SystemExit(f"{site} isn't linked to a Vercel project; run `vercel link` there first.")
    vercel = shutil.which("vercel")
    if vercel is None:
        raise SystemExit("The Vercel CLI isn't installed (npm i -g vercel).")
    subprocess.run([vercel, "deploy", "--prod", "--yes"], cwd=site, check=True)


if __name__ == "__main__":
    main()
