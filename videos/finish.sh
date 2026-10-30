#!/usr/bin/env bash
# Assemble a finished project and run the checks.  Usage: ../finish.sh SNAPSHOT_TIMES
set -e
export PATH="/c/Users/markyjas/AppData/Local/Microsoft/WinGet/Links:$PATH"
S="C:/Users/markyjas/.claude/plugins/cache/hyperframes/hyperframes/0.8.117/skills/product-launch-video/scripts"
CLI="node C:/Users/markyjas/.claude/plugins/cache/hyperframes/hyperframes/0.8.117/skills/hyperframes/scripts/plugin-cli.mjs"
sed -i 's/^- status: \(outline\|built\)$/- status: animated/' STORYBOARD.md
# assemble-index hoists each frame's <video> out of the frame file; keep pristine frames and assemble from them
if [ -d .hyperframes/frames_src ]; then cp .hyperframes/frames_src/*.html compositions/frames/; else mkdir -p .hyperframes/frames_src && cp compositions/frames/*.html .hyperframes/frames_src/; fi
node "$S/assemble-index.mjs" --storyboard ./STORYBOARD.md --hyperframes . 2>&1 | grep -E "frames|voice|bgm|captions|sfx|total duration|HARD|error" || true
/m/Repositories/BGMap/.venv/Scripts/python .hyperframes/videos_under.py
node "$S/transitions.mjs" inject --storyboard ./STORYBOARD.md --hyperframes . >/dev/null
node "$S/transitions.mjs" verify --storyboard ./STORYBOARD.md --index ./index.html | tail -1
$CLI lint 2>&1 | tail -1
$CLI check --json 2>/dev/null > .hyperframes/check.json || true
/m/Repositories/BGMap/.venv/Scripts/python - <<'PY'
import json
d = json.load(open(".hyperframes/check.json", encoding="utf-8")); seen = set()
def walk(o):
    if isinstance(o, dict):
        c = o.get("code", "")
        if (o.get("severity") == "error" or "overflow" in c or "contrast" in c) and (c, o.get("selector")) not in seen:
            seen.add((c, o.get("selector"))); print(" ", o.get("severity"), c, o.get("time"), o.get("selector"), repr(o.get("text", ""))[:50])
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(d)
PY
$CLI snapshot --at "$1" --no-end 2>&1 | tail -1
