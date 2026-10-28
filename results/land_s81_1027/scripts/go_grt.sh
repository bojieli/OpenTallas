#!/bin/bash
# LAND-S81-1: combined die GRT incl. regional clocks = die_trial signal kit (M4-M7 adj 0.75) + region-tree ctree (M8-M9 adj 0.4),
# ONE global_route, 50 congestion iterations (-allow_congestion; overflow reported), TT + FF in parallel, clock arrivals on GRT RC.
# Launch: ot-run --mem 120 --threads 16 --dir $O -- bash go_grt.sh
set -u
WT=/srv/opentallas-scratch2/claude/wt/land-s81-1027; O=/srv/opentallas-scratch2/claude/land-s81-1027
echo START $(date) host $(hostname) code $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $WT/physical/die_plan/s81/die_plan_land.json | cut -c1-12)
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for C in TT FF; do
  CORNER=$C ADJ=0.75 python3 $WT/results/land_s81_1027/scripts/mk_combo_dcm.py $O/kit $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL $C; exit 1; }
  docker run -d --name lands81-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $O/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait lands81-$C; docker rm lands81-$C >/dev/null; done
echo COMBO_DONE $(date)
for C in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10; grep -c "GRT-011[34]" $O/out_$C/combo_$C.log; tail -2 $O/out_$C/combo_$C.log; done
python3 $WT/results/land_s81_1027/scripts/land_report_regions.py $O $O/reg/landed_crossings.json $O/reg/regions.json $O/landed_report.json
echo GRT_DONE $(date)
