#!/bin/bash
# CLOCK-KV-R8 item 4: die related-pair STA on routed b5: AOCV 0.21 %/mm (CLK-AOCV approved table), shared droop,
# CPPR at the signed continuous mesh (per-pair U from the b5 MC, ruling R7 (1) form), then HB4 count.
set -e
D=/srv/opentallas-scratch2/claude/clock-kv-r8-1026; TD=/srv/opentallas-scratch2/claude/wt/clock-kv-r1-1026/tools/die_plan
K7=$TD/kv_r7; K8=$TD/kv_r8; R7=/srv/opentallas-scratch2/claude/clock-kv-r7-1026; A6=/srv/opentallas-scratch2/claude/clock-kv-r6-1026/aocv
cd $D; export PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib:$TD:$K8
U=TT=154.28,FF=147.10; PP=TT=lin/die_TT.json,FF=lin/die_FF.json; PL=$D/d5/plan.json
cp $R7/clk_aocv_table_g021.json .; cp $A6/die_ci_margins.json . 2>/dev/null || true
mkdir -p aocv_b5; python3 $A6/aug.py b5 aocv_b5
python3 $K7/mesh_cppr.py b5 aocv_b5 mcp_b5
ulimit -v 32000000
for C in TT FF; do
  python3 $K8/die_sta_related_r8.py mcp_b5 --plan $PL --out mcp_b5/relp_$C --corner $C --clock-ocv table --clock-droop shared --clock-aocv-table clk_aocv_table_g021.json --mesh-unc $U --mesh-unc-pairs $PP --mesh-routed b5 > mcp_b5/relp_$C.log 2>&1 || echo rc=$?
done
grep -h -v SUMMARY mcp_b5/relp_TT.log mcp_b5/relp_FF.log
HB_OUT=mcp_b5/hb_pairU.json python3 $K8/hb_count_r8.py $TD $PL mcp_b5 $K8 $D/clk_aocv_table_g021.json $U $PP b5 | cut -c1-900
echo STA_DONE $(date -Is)
