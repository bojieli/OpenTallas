#!/bin/bash
# PATH-HBM-R14: die GRT INCLUDING CLOCK on plan $1 (F2|S2), after hbm_hub_clock_retarget (all core taps bound to placed replicas).
# die_trial kit (signals, M5-ceiling cores) -> die_clock_mesh build (ONE continuous mesh, 12.8 default, fixed VSS-shielded tree pre-routes)
# -> balance (structural audit, no pads) -> combo global_route 50 it TT+FF (kit signals + mesh clock) -> post (mesh RC + stub STA + report) -> render
set -e
P=$1; O=/srv/opentallas-scratch2/claude/path-hbm-r14-1026; WT=/srv/opentallas-scratch2/claude/wt/path-hbm-r14-1026; T=$WT/tools/die_plan
D=$O/run$P; PLAN=$O/plan$P/die_plan.json; mkdir -p $D
echo START $P $(date) src=$(git -C $WT rev-parse --short HEAD) plan=$(sha256sum $PLAN | cut -c1-12)
cd $WT
python3 $T/die_trial.py kit $PLAN --out $D/kit > $D/kit_build.log 2>&1; echo KIT rc=$? $(date)
grep -c "congestion_iterations 50 " $D/kit/grt/grt.tcl
python3 $T/die_clock_mesh.py build $PLAN --out $D/mesh --nx 64 --ny 32 --clock-floorplan $O/clock_floorplan_r14.json --reserve-cell-sites --delta-id D-HBM-CLKMESH-R14 > $D/mesh_build.log 2>&1; echo BUILT rc=$? $(date)
python3 $T/die_clock_mesh.py balance $D/mesh --out $D/mesh_b --plan $PLAN > $D/balance.log 2>&1; echo AUDIT rc=$? $(date)
python3 $T/die_clock_mesh.py combo $D/mesh_b --kit $D/kit --plan $PLAN > $D/combo_gen.log 2>&1; echo COMBOGEN rc=$? $(date)
grep -c "congestion_iterations 50" $D/mesh_b/combo.tcl || true
MEM=48 CORNERS="TT FF" bash $D/mesh_b/run_combo.sh || true
echo COMBO $(date) $(grep -h "^EXIT" $D/mesh_b/combo_TT.log $D/mesh_b/combo_FF.log | tr "\n" " ")
for c in TT FF; do echo $c; grep -c "GRT-011[34]" $D/mesh_b/combo_$c.log; grep "^Total" $D/mesh_b/combo_$c.log | tail -n1; done
CORNERS="TT FF" bash $T/die_clock_mesh_post.sh $D/mesh_b $PLAN > $D/post.log 2>&1 || echo POST_FAIL
python3 $T/die_clock_mesh.py render $D/mesh_b --plan $PLAN --out $D/mesh_b/mesh.png || true
rm -f $D/mesh_b/*.odb
echo ALL_DONE $(date)
