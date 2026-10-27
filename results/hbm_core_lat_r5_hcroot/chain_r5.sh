#!/bin/bash
# HBM-CORE-LAT-R5 hcp_sys1 chain AFTER synth LEC EQUIVALENT (CMD_RST=1 netlist; the R4 4_cts.odb is no longer valid):
# place (fp_place.sh) -> R3 plan tool (run_plan.sh: geo dump -> core_trunk_plan candidates -> fixed choice rule) ->
# mscts_spec.tcl (frozen named membership of the NEW netlist; port ck->clk) -> plan-built CTS + FF hold gate (cts_r4.sh)
# -> run_kit_hbm.sh route (GRT BC hold repair -> per-corner insertion gate -> DRT -> finish -> abstract -> corners -> signoff)
# -> routed LEC (6_final.v vs kit RTL).  No clock edits (OT_MSCTS_ITERS=0, POST_CTS report-only).
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); W=/srv/opentallas-scratch2/claude/wt/hbm-core-lat-r5; P=$K/plan_r5
st(){ echo "R5CHAIN $* $(date -Is)" | tee -a $K/chain_r5.status; }
st start
grep -q '"verdict": *"EQUIVALENT"' $K/lec/lec.json || { st ABORT synth LEC not EQUIVALENT; exit 3; }
bash $K/fp_place.sh; rc=$?; st place rc $rc; [ $rc = 0 ] || exit $rc
bash $W/results/hbm_core_lat_r3_hcroot/run_plan.sh $K $P hcp_sys1 > $K/plan_r5.log 2>&1; rc=$?; st plan rc $rc $(grep CHOSEN $K/plan_r5.log); [ $rc = 0 ] || exit $rc
sed 's/^set ot_ms_port ck$/set ot_ms_port clk/' $P/hcp_sys1.tree_spec.tcl > $K/mscts_spec.tcl
bash $K/cts_r4.sh; rc=$?; st cts rc $rc $(grep -h "OT_R4_MEMBERSHIP\|OT_HOLD_GATE" $K/cts_r4.log | tr '\n' ' '); [ $rc = 0 ] || exit $rc
bash $K/run_kit_hbm.sh $K route 24 8; rc=$?; st run_kit_route rc $rc
F=$(ls $K/run/results/asap7/*/base/6_final.v 2>/dev/null | head -1)
if [ -n "$F" ]; then python3 -I $K/lec.py $K --netlist $F --out $K/lec_routed --jobs 8 --mem 32 > $K/lec_routed.log 2>&1; lr=$?; st lec_routed rc $lr $(tail -1 $K/lec_routed.log); fi
exit $rc
