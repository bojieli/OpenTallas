#!/bin/bash
# FLOW-27 11-04 (COORD 05:36 (3)): generate one canary set for one sha on epyc4 scratch3, nothing on intel2. Does NOT launch:
# ot-run has no working host list on epyc4, so flow_canary_ep4_tick.py on intel2 drives the printed runs (--hosts epyc4).
# Run ON epyc4:  canary_tag_epyc4.sh <sha> [die ...]   Prints: RUN <tab> die <tab> run dir <tab> mem <tab> threads <tab> src-or-dash
set -eu
SHA=$1; shift
REPO=/home/ubuntu/OpenTallas; ROOT=/srv/opentallas-scratch3/claude/flow-canary; RUNS=$ROOT/runs
mkdir -p "$RUNS"
git -C "$REPO" fetch -q origin main
FULL=$(git -C "$REPO" rev-parse "$SHA^{commit}")
T=$(mktemp -d "$ROOT/tool.XXXX"); trap 'rm -rf "$T"' EXIT
git -C "$REPO" archive "$FULL" tools/flow_canary | tar -x -C "$T"
SRC=$(python3 -I - "$T/tools/flow_canary" "$REPO" "$FULL" "$RUNS" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import trigger
print(trigger.source_snapshot(sys.argv[2], sys.argv[3], sys.argv[4]))
PY
)
DIES=(); for d in "$@"; do DIES+=(--die "$d"); done
python3 -I "$SRC/tools/flow_canary/canary.py" submit --dry --src "$SRC" --root "$RUNS" "${DIES[@]}" > "$T/out"
cat "$T/out" | grep -v '^  DRY' || true
python3 -I - "$T/out" "$SRC" <<'PY'
import json, re, sys
for line in open(sys.argv[1]):
    m = re.match(r"CANARY (\S+) .*: (/\S+)$", line.strip())
    if m:
        spec = json.load(open(m.group(2) + "/canary_meta.json"))["spec"]
        print("RUN", m.group(1), m.group(2), spec["mem_gb"], spec.get("threads", 8), sys.argv[2] if "{src}" in spec.get("run", "") else "-", sep="\t")
PY
