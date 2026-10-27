#!/bin/bash
# FALLBACK-HEAD FB1: die_trial kit on the one-entry-per-partition variant + combined die GRT (signals M4-M7 adj 0.75,
# die ctree M8-M9 adj 0.4, ONE global_route, 50 congestion iterations) TT+FF + native clock arrivals (read-only probe)
set -u
WT=/srv/opentallas-scratch2/claude/wt/fallback-head-1026; O=/srv/opentallas-scratch2/claude/fallback-head-1026; R=~/.local/bin/ot-run
J=$O/fb1_plan.json
echo START $(date) code $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $J | cut -c1-12)
$R --mem 24 --threads 4 --dir $O --stage $WT --stage $O -- bash -c "cd $WT && python3 tools/die_plan/die_trial.py kit $J --out $O/kit" > $O/kit_build.log 2>&1 || { echo KIT_FAIL $(date); exit 1; }
echo KIT_OK $(date); ls $O/kit/clock
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for CORNER in TT FF; do
  CORNER=$CORNER ADJ=0.75 python3 $O/bin/mk_combo_dcm.py $O/kit $O/clk $O/out_$CORNER > $O/mk_$CORNER.log 2>&1 || { echo MK_FAIL; exit 1; }
  docker run -d --name fbhead-$CORNER --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$CORNER -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $O/kit:/work:ro -v $O/out_$CORNER:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$CORNER.log 2>&1; echo EXIT \$? >> /out/combo_$CORNER.log; chown -R $(id -u):$(id -g) /out"
done
for CORNER in TT FF; do docker wait fbhead-$CORNER; docker rm fbhead-$CORNER >/dev/null; done
echo COMBO_DONE $(date)
for CORNER in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$CORNER/combo_$CORNER.log | tail -10; grep -c "GRT-011[34]" $O/out_$CORNER/combo_$CORNER.log; tail -2 $O/out_$CORNER/combo_$CORNER.log; done
