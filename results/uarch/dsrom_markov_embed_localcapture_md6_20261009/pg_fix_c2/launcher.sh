#!/bin/bash
set -eu
D=/srv/opentallas-scratch/claude/md6-pg-fix-c2c07c284
docker run --rm -v /srv/opentallas-scratch/claude/md6-pg-diag-a1/6_final.odb:/evidence/6_final.odb:ro -v "$D/source:/src:ro" -v "$D:/receipt" sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init /receipt/check.tcl' > "$D/check.log" 2>&1
python3 "$D/source/tools/fp_margin_lint.py" check "$D/fp_dump.json" --out "$D/fp_lint.json" > "$D/fp_lint.log" 2>&1
