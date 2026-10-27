#!/bin/bash
# FALLBACK-S81-2 v5.0: composed G=2 plan WITH early core taps (macro insertion-delay balancing) -> latency regen -> G0 -> kit + render
set -eu
WT=/srv/opentallas-scratch2/claude/wt/fallback-s81-2-1026; O=/srv/opentallas-scratch2/claude/fallback-s81-2-1026; PD=$O/plandir
cd $WT; J=$PD/die_plan_fb2_g2_tap.json; cp $O/plan_g2_r1.json $J
python3 tools/die_plan/gen.py latency $J --inplace --out $O/gen_lat_tap > $O/gen_lat_tap.log 2>&1
python3 tools/die_plan/check.py $J --out $O/g0_tap > $O/g0_tap.log 2>&1 || true; tail -1 $O/g0_tap.log
python3 tools/die_plan/die_trial.py kit $J --out $O/kit_tap --htree-full-depth --leaf-um 300 --tree-site-legal \
  --region-trees results/fallback_s81_2_1026/regions/class_g2_tap/regions.json > $O/kit_tap_build.log 2>&1
python3 results/fallback_s81_2_1026/scripts/render_regions_tree.py $J results/fallback_s81_2_1026/regions/class_g2_tap/regions.json \
  $O/kit_tap/clock/tree.json $O/kit_tap/tree_regions.png $O/kit_tap/tree_summary.json > $O/render_tap.log 2>&1
echo GEN_DONE $(date)
