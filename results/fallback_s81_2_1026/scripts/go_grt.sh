#!/bin/bash
# FALLBACK-S81-2: combined die GRT incl. clock = die_trial signal kit (M4-M7 adj 0.75) + region-tree ctree (M8-M9 adj 0.4),
# ONE global_route, 50 congestion iterations, TT + FF in parallel, native clock arrivals on GRT RC (mk_combo_dcm, FALLBACK-HEAD recipe).
# Launch: ot-run --mem 120 --threads 16 --dir $O -- bash go_grt.sh
set -u
WT=/srv/opentallas-scratch2/claude/wt/fallback-s81-2-1026; O=/srv/opentallas-scratch2/claude/fallback-s81-2-1026
echo START $(date) host $(hostname) code $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $O/plandir/die_plan_fb2_g2_tap.json | cut -c1-12)
mkdir -p $O/clk; cp $O/kit_tap/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for C in TT FF; do
  CORNER=$C ADJ=0.75 python3 $WT/results/fallback_s81_2_1026/scripts/mk_combo_dcm.py $O/kit_tap $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL $C; exit 1; }
  docker run -d --name fbs81b-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $O/kit_tap:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait fbs81b-$C; docker rm fbs81b-$C >/dev/null; done
echo COMBO_DONE $(date)
for C in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10; grep -c "GRT-011[34]" $O/out_$C/combo_$C.log; tail -2 $O/out_$C/combo_$C.log; done
