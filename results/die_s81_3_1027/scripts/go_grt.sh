#!/bin/bash
# DIE-S81-3: die GRT incl clock = die_trial signal kit (M4-M7 adj 0.75) + link_fishbone feed / balanced region H-trees
# (M8-M9 adj 0.4) in ONE global_route, 50 congestion iterations, TT + FF in parallel; clock arrivals on GRT RC
# (mk_combo_dcm.py of LAND-S81-1, reused).  Launch: ot-run --mem 120 --threads 16 --dir $O -- bash go_grt.sh
set -u
WT=/srv/opentallas-scratch2/claude/wt/die-s81-3; O=/srv/opentallas-scratch2/claude/die-s81-3
echo START $(date) host $(hostname) code $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $O/die_plan_r98.json | cut -c1-12)
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for C in TT FF; do
  CORNER=$C ADJ=0.75 python3 $WT/results/land_s81_1027/scripts/mk_combo_dcm.py $O/kit $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL $C; exit 1; }
  docker run -d --name dies81-3-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $O/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait dies81-3-$C; docker rm dies81-3-$C >/dev/null; done
echo COMBO_DONE $(date)
for C in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10; grep -c "GRT-011[34]" $O/out_$C/combo_$C.log; tail -2 $O/out_$C/combo_$C.log; done
echo GRT_DONE $(date)
