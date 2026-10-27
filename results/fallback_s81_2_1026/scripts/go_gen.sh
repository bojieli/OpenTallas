#!/bin/bash
# FALLBACK-S81-2: composed G=2 plan -> no-early-tap delta -> regenerated latency table -> G0 -> die_trial kit with
# region local trees (--htree-full-depth --leaf-um 300 --tree-site-legal --region-trees) -> render
set -eu
WT=/srv/opentallas-scratch2/claude/wt/fallback-s81-2-1026; O=/srv/opentallas-scratch2/claude/fallback-s81-2-1026
SRC=/srv/opentallas-scratch2/claude/path-s81-taps-1026/src/physical/die_plan/s81
PD=$O/plandir; mkdir -p $PD; for d in bind census cores inputs lat r8 synth; do ln -sfn $SRC/$d $PD/$d; done
cd $WT
J=$PD/die_plan_fb2_g2.json
python3 results/fallback_s81_2_1026/scripts/fb2_delta.py $O/plan_g2_r1.json $J
python3 tools/die_plan/gen.py latency $J --inplace --out $O/gen_lat > $O/gen_lat.log 2>&1
python3 tools/die_plan/check.py $J --out $O/g0_fb2 > $O/g0_fb2.log 2>&1 || true
tail -1 $O/g0_fb2.log
python3 tools/die_plan/die_trial.py kit $J --out $O/kit --htree-full-depth --leaf-um 300 --tree-site-legal \
  --region-trees results/fallback_s81_2_1026/regions/class_g2_land/regions.json > $O/kit_build.log 2>&1
python3 results/fallback_s81_2_1026/scripts/render_regions_tree.py $J results/fallback_s81_2_1026/regions/class_g2_land/regions.json \
  $O/kit/clock/tree.json $O/kit/tree_regions.png $O/kit/tree_summary.json > $O/render.log 2>&1
echo GEN_DONE $(date)
