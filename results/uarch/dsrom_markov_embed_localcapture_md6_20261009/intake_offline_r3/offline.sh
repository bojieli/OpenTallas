#!/bin/bash
set -eu
D=/srv/opentallas-scratch/claude/md6-z7-intake-f59bf7441
python3 "$D/preflight.py" > "$D/helper_preflight.json"
docker run --rm -v "$D/source:/src:ro" -v "/srv/opentallas-scratch/claude/md6-z7-intake-8d5a1fe5f/floorplan_r1/work/orfs:/work:ro" -v "$D:/receipt" sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init /receipt/offline.tcl' > "$D/offline.log" 2>&1
python3 "$D/source/tools/fp_margin_lint.py" check "$D/anchored_fp_dump.json" --out "$D/offline_fp_lint.json" > "$D/offline_fp_lint.log" 2>&1
