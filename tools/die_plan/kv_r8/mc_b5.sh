#!/bin/bash
# CLOCK-KV-R8 item 2: whole-die linear mesh MC on routed b5 (QC-CLK-MESH-2 method, same args as R7), TT+FF 12 samples
set -e
D=/srv/opentallas-scratch2/claude/clock-kv-r8-1026; K=/srv/opentallas-scratch2/claude/wt/clock-kv-r1-1026/tools/die_plan/kv_r7
export PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib; cd $D
python3 $K/../kv_r8/kv_mesh_rec.py $D/b5 $D/rec_b5.json
for C in TT FF; do python3 $K/qc_clk_mesh2.py solve rec_b5.json --thev /srv/opentallas-scratch2/claude/clock-kv-r7-1026/thev_qc_m2.json --corner $C --samples 12 --ndr 4w --out lin/die_$C.json > lin/die_$C.log 2>&1 & done
wait; echo MC_DONE $(date -Is)
