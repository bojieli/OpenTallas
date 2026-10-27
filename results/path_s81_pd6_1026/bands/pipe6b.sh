#!/bin/bash
# PATH-S81-PD6: restart of pipe6.sh from compose (first run stopped at compose: plan-relative inputs cores/, census/ ...
# were missing next to the PD6 plan; now symlinked from PD5 src_b2c). Plan die_plan_pd6_f.json unchanged (b53f2b8c).
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/path-s81-pd5-1026-git; O=/srv/opentallas-scratch2/claude/path-s81-pd6-1026
D=$O/src; P=$D/die_plan_pd6_f.json; C=$D/die_plan_pd6_composed.json
cd $W
echo RESTART $(date) plan $(sha256sum $P | cut -c1-12)
(python3 tools/die_plan/check.py $P --out $O/g0_pd6 --png > $O/g0_pd6.log 2>&1 || true) &
python3 $W/results/fallback_s81_1026/compose_plan.py "$P" $O/regions/landed_crossings.json "$C" $O/side.json > $O/compose.log 2>&1
cat $O/compose.log
python3 tools/die_plan/gen.py latency "$C" --inplace --out $O/gen_lat_composed > $O/gen_lat_composed.log 2>&1
(python3 tools/die_plan/check.py "$C" --out $O/g0_composed --png > $O/g0_composed.log 2>&1 || true) &
python3 tools/die_plan/die_trial.py kit "$C" --out $O/kit --htree-full-depth --leaf-um 300 --tree-site-legal --tree-site-slide --tap-rep-um 405 \
  --region-trees $O/regions/regions.json > $O/kit_build.log 2>&1
tail -3 $O/kit_build.log
python3 $W/results/fallback_s81_2_1026/scripts/render_regions_tree.py "$C" $O/regions/regions.json $O/kit/clock/tree.json $O/kit/tree_regions.png $O/kit/tree_summary.json > $O/render_tree.log 2>&1 || echo RENDER_FAIL
wait
grep -E "G0C|G0 (FAIL|PASS)" $O/g0_pd6.log | cut -c1-300; grep -E "G0C|G0 (FAIL|PASS)" $O/g0_composed.log | cut -c1-300
sha256sum $C
echo KIT_DONE $(date)
