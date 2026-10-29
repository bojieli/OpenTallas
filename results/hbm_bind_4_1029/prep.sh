#!/usr/bin/env bash
set -u
R=/srv/opentallas-scratch2/claude/hbm-bind-4-1029; W=/srv/opentallas-scratch2/claude/wt/hbm-bind-4-1029; C=/srv/opentallas-scratch2/claude/codex-hbm-bind-0850
mkdir -p $R/dce $R/norm
python3 $W/tools/hbm_b2/dead_scorer_loop_index.py $C/combined/out/asbuilt.json --out $R/dce/asbuilt.json --receipt $R/dce/receipt.json > $R/dce/log 2>&1 || { echo DCE_FAIL; exit 1; }
cat $R/dce/log
python3 $W/results/hbm_bind_4_1029/normalize_mem.py $R/dce/asbuilt.json --out $R/norm/asbuilt.json --receipt $R/norm/receipt.json --map-in $C/map_rebased.json --map-out $R/norm/map_norm.json > $R/norm/log 2>&1; rc=$?
cat $R/norm/log | tail -5; exit $rc
