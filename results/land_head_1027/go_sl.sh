#!/bin/bash
# LAND-HEAD-1: landed s81_head on plan 7af81995 (+compose dataflow, latency regen, FB1 one entry/partition):
# die_trial kit sl300 recipe (--htree-full-depth --leaf-um 300 --tree-site-slide) + combined die GRT (signals M4-M7 adj 0.75,
# die ctree M8-M9 adj 0.4, ONE global_route, 50 congestion iterations) TT then FF + native clock arrivals + landed |d| report.
set -u
WT=/srv/opentallas-scratch2/claude/wt/land-head-1; O=/srv/opentallas-scratch2/claude/land-head-1/sl300
J=/srv/opentallas-scratch2/claude/land-head-1/compose/fb1_lat.json
mkdir -p $O; cd $WT
echo START $(date) code $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $J | cut -c1-12) host $(hostname)
python3 tools/die_plan/die_trial.py kit $J --out $O/kit --leaf-um 300 --htree-full-depth --tree-site-slide > $O/kit_build.log 2>&1 || { echo KIT_FAIL $(date); tail -20 $O/kit_build.log; exit 1; }
echo KIT_OK $(date)
python3 tools/die_plan/die_trial.py render $O/kit --plan $J > $O/render.log 2>&1 || echo RENDER_FAIL
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for CORNER in TT FF; do
  CORNER=$CORNER ADJ=0.75 python3 $WT/results/fallback_head_1026/scripts/mk_combo_dcm.py $O/kit $O/clk $O/out_$CORNER > $O/mk_$CORNER.log 2>&1 || { echo MK_FAIL; tail $O/mk_$CORNER.log; exit 1; }
  docker run --rm --name landhead-$CORNER-$$ --memory=40g --memory-swap=40g --cpus=8 -e CORNER=$CORNER -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $O/kit:/work:ro -v $O/out_$CORNER:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$CORNER.log 2>&1; echo EXIT \$? >> /out/combo_$CORNER.log; chown -R $(id -u):$(id -g) /out"
  grep -E "^(M[1-9]|Total) " $O/out_$CORNER/combo_$CORNER.log | tail -10; echo "GRT-0113/4: $(grep -c 'GRT-011[34]' $O/out_$CORNER/combo_$CORNER.log)"; tail -2 $O/out_$CORNER/combo_$CORNER.log
done
echo COMBO_DONE $(date)
python3 tools/s81_head/fallback_land_report.py $J $O --png $O/landed_sl300.png > $O/report.log 2>&1; tail -30 $O/report.log
echo END $(date)
