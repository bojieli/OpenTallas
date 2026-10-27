#!/bin/bash
# run_mcp.sh OUTDIR [mesh_cppr extra args]: mesh-CPPR copy of b3 -> die STA (AOCV table, die-wide U and per-pair U) -> HB4 counts
set -e
R=/srv/opentallas-scratch2/claude/clock-kv-r7-1026; T6=/srv/opentallas-scratch2/claude/clock-kv-r6-1026; TD=/srv/opentallas-scratch2/claude/wt/clock-kv-r7-1026/tools/die_plan; K=$TD/kv_r7
cd $R; O=$1; shift; export PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib:$TD
U=${U:-TT=131.62,FF=117.97}; P=${P:-TT=lin/die_TT.json,FF=lin/die_FF.json}
python3 $K/mesh_cppr.py $T6/b3 $T6/aocv_b3 $O "$@"
ulimit -v 32000000
for C in TT FF; do
  python3 $K/die_sta_related_r7.py $O --plan $T6/d3/plan.json --out $O/rel_$C --corner $C --clock-ocv table --clock-droop shared --clock-aocv-table clk_aocv_table_g021.json --mesh-unc $U > $O/rel_$C.log 2>&1 || echo rc=$?
  python3 $K/die_sta_related_r7.py $O --plan $T6/d3/plan.json --out $O/relp_$C --corner $C --clock-ocv table --clock-droop shared --clock-aocv-table clk_aocv_table_g021.json --mesh-unc $U --mesh-unc-pairs $P --mesh-routed $T6/b3 > $O/relp_$C.log 2>&1 || echo rc=$?
done
grep -h -v SUMMARY $O/rel_TT.log $O/rel_FF.log | sed 's/^/dieU  /'; grep -h -v SUMMARY $O/relp_TT.log $O/relp_FF.log | sed 's/^/pairU /'
HB_OUT=$O/hb_dieU.json python3 $K/hb_count_r7.py $TD $T6/d3/plan.json $O $K $R/clk_aocv_table_g021.json $U | cut -c1-700
HB_OUT=$O/hb_pairU.json python3 $K/hb_count_r7.py $TD $T6/d3/plan.json $O $K $R/clk_aocv_table_g021.json $U $P $T6/b3 | cut -c1-700
