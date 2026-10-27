#!/bin/bash
# PATH-S81-PD5: regions (ii) [--hard-merge inputs + 2x2 svc groups] -> landed compose (landing contract / bands) -> latency -> G0 -> kit
# with the structural clock delta (full-depth equal-level H-tree, site-legal+slide, leaf 300, leaf->tap repeaters <=405 um, region trees)
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/path-s81-pd5-1026; O=/srv/opentallas-scratch2/claude/path-s81-pd5-1026; D=$O/src_b2c
P=$D/die_plan_pd5_f.json; C=$D/die_plan_pd5_composed.json
cd $W
echo START $(date) code $(git -C $W rev-parse --short HEAD) plan $(sha256sum $P | cut -c1-12)
python3 tools/die_plan/gen.py latency "$P" --inplace --out $O/gen_lat_base > $O/gen_lat_base.log 2>&1
python3 tools/die_plan/fallback_regions.py plan "$P" --lat $O/gen_lat_base/s81_latency.json --out $O/regions --block 2 --core tap --hard-merge inputs --groups $W/results/path_s81_pd_1026/scripts/svc_groups.json > $O/regions.log 2>&1
python3 $W/results/fallback_s81_1026/compose_plan.py "$P" $O/regions/landed_crossings.json "$C" $O/side.json > $O/compose.log 2>&1
cat $O/compose.log
python3 tools/die_plan/gen.py latency "$C" --inplace --out $O/gen_lat_composed > $O/gen_lat_composed.log 2>&1
python3 tools/die_plan/check.py "$C" --out $O/g0_composed --png > $O/g0_composed.log 2>&1 || true
tail -2 $O/g0_composed.log
python3 tools/die_plan/die_trial.py kit "$C" --out $O/kit --htree-full-depth --leaf-um 300 --tree-site-legal --tree-site-slide --tap-rep-um 405 \
  --region-trees $O/regions/regions.json > $O/kit_build.log 2>&1
tail -3 $O/kit_build.log
python3 $W/results/fallback_s81_2_1026/scripts/render_regions_tree.py "$C" $O/regions/regions.json $O/kit/clock/tree.json $O/kit/tree_regions.png $O/kit/tree_summary.json > $O/render_tree.log 2>&1 || echo RENDER_FAIL
echo KIT_DONE $(date)
