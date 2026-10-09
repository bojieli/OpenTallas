#!/bin/bash
# kv-die 2026-10-09: die-level evidence chain for the ROM die (r22k) and the KV die, on a remote host (memory-gated):
#   real case (legality, on-track assert, pin access) -> PDN -> full-die GRT (adjfix: M4/M5 0.30, M6-M9 0.05, signals
#   M4-M9, clock / reset nets special = CTS) -> STA TT setup / FF hold on GRT parasitics (estimate_parasitics
#   -global_routing; element views = the ASSUMED single-flop interface constants of tools/qwen_die_element_lib.py +
#   the HBM PHY abstract) -> classes.
# usage: die_chain.sh <die: kv|r22k> <run dir with case_<die>/ and libs/> <src tree>
set -u
DIE=$1; R=$(readlink -f $2); SRC=$3
H=$(dirname $(readlink -f $0))
C=$R/case_$DIE; G=$R/grt_$DIE          # unique dir names: run_case.sh / dietop_run.sh name containers after them
ADMIT=/srv/opentallas-scratch/admit.sh
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
case $DIE in kv) P1=20; P2=40; P3=60; P4=40;; r22k) P1=40; P2=130; P3=160; P4=110;; *) echo bad die; exit 2;; esac
say "chain start die=$DIE src=$(cat $C/SOURCE_COMMIT 2>/dev/null)"
$ADMIT $P1 -- $H/run_case.sh $C run.tcl run.log 16 $((P1+40))
grep -q OT_LEGAL $C/run.log || { say "REAL CASE FAIL ($C/run.log)"; exit 1; }
say "real case: $(grep -m4 -E 'OT_LEGAL|OT_ASSERT|OT_PA' $C/run.log | tr '\n' ' ')"
$ADMIT $P2 -- $H/run_case.sh $C run_pdn.tcl run_pdn.log 8 $((P2+60))
grep -q "OT_PDN PASS" $C/run_pdn.log || { say "PDN FAIL ($C/run_pdn.log)"; exit 1; }
say "PDN PASS $(grep -m2 OT_PGCHECK $C/run_pdn.log | tr '\n' ' ')"
mkdir -p $G; cp $H/grt.tcl $G/; ln -f $C/floorplan_pdn.odb $G/floorplan_pdn.odb
$ADMIT $P3 -- $H/dietop_run.sh $G grt.tcl 16 $((P3+80)) OT_ITERS=30 OT_TILE_UM=4.8
OV=$(awk '/Final congestion report/{f=1} f && /^Total/{print $NF; exit}' $G/grt.log)
say "full-die GRT exit=$(cat $G/run.exit) overflow=${OV:-none} ($(grep -m1 'Total wirelength' $G/grt.log))"
for c in tt ff; do D=$R/sta_${DIE}_$c; mkdir -p $D/libs
  ln -f $G/ckpt_grt.odb $G/route.guide $G/die_grt.spef $D/
  cp $R/libs/qfd_elements_$c.lib $D/libs/; [ -f $R/libs/qfd_etm_$c.lib ] && cp $R/libs/qfd_etm_$c.lib $R/libs/views.json $D/libs/; [ -f $R/libs/ot_hbm3e_phy_$c.lib ] && cp $R/libs/ot_hbm3e_phy_$c.lib $D/libs/
  python3 $H/sta_tcl.py $DIE $c $D/grt_$c.tcl
  $ADMIT $P4 -- $H/dietop_run.sh $D grt_$c.tcl 8 $((P4+60))
  say "STA $c: $(grep -E '^(wns|tns|worst slack)' $D/grt_$c.log | tr '\n' ' ')"
done
say "chain done"
