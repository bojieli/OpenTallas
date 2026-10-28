#!/bin/bash
# DIE-S81-12: local form (re-treed feed sb5) clock build = main die_trial link_htree (balanced H-tree per region, feed along
# the data links) leaf 200 / rep 250 / --tree-site-slide on plan_s10, then die GRT incl clock TT+FF (50 it, crit 0; S81-4 recipe)
set -u
W=/srv/opentallas-scratch2/claude/wt/die-s81-12; O=/srv/opentallas-scratch2/claude/die-s81-12; R=/srv/opentallas-scratch2/claude/wt/die-s81-12/results/die_s81_12_1028/scripts; PL=/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json
echo START $(date) host $(hostname) code $(git -C $W rev-parse --short HEAD) plan $(sha256sum $PL | cut -c1-12) feed $(sha256sum $O/feed_sb5.json | cut -c1-12)
python3 $W/tools/die_plan/die_trial.py kit $PL --out $O/kit --leaf-um 200 --rep-um 250 --tree-form link_htree --feed $O/feed_sb5.json --region-trees $O/map398.json --tree-site-slide > $O/kit.log 2>&1
echo KIT_RC $? $(date); tail -3 $O/kit.log
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/ || exit 1; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for C in TT FF; do
  mkdir -p $O/out_$C
  CORNER=$C ADJ=0.75 python3 $R/mk_combo_dcm.py $O/kit $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL $C; exit 1; }
  docker run -d --name dies81-12-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait dies81-12-$C; docker rm dies81-12-$C >/dev/null; done
echo COMBO_DONE $(date)
for C in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10; tail -2 $O/out_$C/combo_$C.log; done
echo GRT_DONE $(date)
