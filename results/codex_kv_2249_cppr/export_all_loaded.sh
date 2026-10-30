#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-kv-2249
mkdir proof_all_core
cp proof_loaded/{mesh.json,droop_regions.json} proof_all_core/
for C in TT FF; do
 python3 src/tools/die_plan/trial_tap_arrivals.py /srv/opentallas-scratch2/claude/die-kv-42-1029/stgrt/clkgrt_st/tree.json edges_$C/arr_$C.txt "$C" proof_all_core/tap_arrivals_$C.json --node-cell-names >export_all_$C.txt
done
python3 src/tools/die_plan/start_stage_emit.py proof proof_all_core --stages /srv/opentallas-scratch2/claude/die-kv-41-1029/start_wc/emitted/start_stages.json --arr TT=edges_TT/arr_TT.txt --arr FF=edges_FF/arr_FF.txt --out proof_all_loaded
cp /srv/opentallas-scratch2/claude/die-kv-41-1029/start_wc/emitted/ctree.v proof_all_loaded/
