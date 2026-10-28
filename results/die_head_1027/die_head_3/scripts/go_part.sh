#!/bin/bash
# DIE-HEAD-3: d150 event -> FB1 kit (spine_fishbone rep 250, site slide) -> die GRT incl clock TT+FF (50 it, cnp 0) -> arrivals
set -u
WT=/srv/opentallas-scratch2/claude/wt/die-head-1; E=/srv/opentallas-scratch2/claude/die-head-3/part/event; O=$E/grt
mkdir -p $O; cd $WT; echo START $(date) code $(git rev-parse --short HEAD) plan $(sha256sum $E/part_fb1.json | cut -c1-12) host $(hostname)
python3 tools/die_plan/die_trial.py kit $E/part_fb1.json --out $O/kit --tree-form spine_fishbone --tree-site-slide --rep-um 250 > $O/kit.log 2>&1 || { echo KIT_FAIL; tail $O/kit.log; exit 1; }
python3 tools/die_plan/die_trial.py render $O/kit --plan $E/part_fb1.json > $O/render.log 2>&1 || echo RENDER_FAIL
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
cmp $O/clk/tree.json /srv/opentallas-scratch2/claude/die-head-1/sfb250c/clk/tree.json && echo TREE_IDENTICAL_TO_SFB250C
for C in TT FF; do
  CORNER=$C ADJ=0.75 python3 $WT/results/fallback_head_1026/scripts/mk_combo_dcm.py $O/kit $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL; tail $O/mk_$C.log; exit 1; }
  sed -i "s/-congestion_iterations 50 -allow/-congestion_iterations 50 -critical_nets_percentage 0 -allow/" $O/out_$C/combo.tcl
done
for C in TT FF; do
  docker run --rm --name dh3-part-$C-$$ --memory=40g --memory-swap=40g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $O/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out" &
done
wait
for C in TT FF; do echo == $C; grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10; echo "GRT-0113/4: $(grep -c 'GRT-011[34]' $O/out_$C/combo_$C.log) cong-iter-lines: $(grep -ci 'congestion iteration' $O/out_$C/combo_$C.log)"; grep -i "critical_nets\|congestion_iterations" $O/out_$C/combo.tcl | head -2; tail -2 $O/out_$C/combo_$C.log; done
for C in TT FF; do cmp $O/out_$C/arr_$C.txt /srv/opentallas-scratch2/claude/die-head-1/sfb250c/out_$C/arr_$C.txt && echo ARR_${C}_IDENTICAL; done
echo END $(date)
