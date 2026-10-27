#!/bin/bash
# PATH-S81-PD6: PD5 plan (after stations + bk_tx64: die_plan_pd5_tx.json) -> band core shifts -> PHY density taps ->
# tap prune/regen (as pipe5) -> merge the 3 identical b1 frame types -> G0 -> regions -> compose -> latency -> G0 -> kit -> render
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/path-s81-pd5-1026-git; O=/srv/opentallas-scratch2/claude/path-s81-pd6-1026; P5=/srv/opentallas-scratch2/claude/path-s81-pd5-1026
S=$W/physical/die_plan/s81; D=$O/src; mkdir -p $D; cd $D
echo START $(date) code $(git -C $W rev-parse --short HEAD)
python3 $S/apply_band_core_shift_1026.py $P5/src_b2c/die_plan_pd5_tx.json die_plan_pd6_sh.json $O/bands/shift_base.json $O/bands/shift_ledger.json
(cd $W/tools/die_plan && python3 s81_phy_clock_keepouts.py $D/die_plan_pd6_sh.json $D/die_plan_pd6_phy.json --report $O/pd6_phy_density.json --density)
L0=/srv/opentallas-scratch2/claude/path-s81-taps-1026/taps_ledger.json
python3 $S/prune_ftphy_taps_1026.py $W die_plan_pd6_phy.json die_plan_pd6_pr.json $L0 $O/pd6_taps_pruned.json
python3 $S/regen_explicit_taps_1026.py $W die_plan_pd6_pr.json die_plan_pd6_r1.json $O/pd6_taps_ledger1.json | tail -2
python3 $S/prune_ftphy_taps_1026.py $W die_plan_pd6_r1.json die_plan_pd6_p2.json $L0,$O/pd6_taps_ledger1.json $O/pd6_taps_pruned2.json
python3 $S/regen_explicit_taps_1026.py $W die_plan_pd6_p2.json die_plan_pd6_r2.json $O/pd6_taps_ledger2.json | tail -2
python3 $S/prune_ftphy_taps_1026.py $W die_plan_pd6_r2.json die_plan_pd6_f0.json $L0,$O/pd6_taps_ledger1.json,$O/pd6_taps_ledger2.json $O/pd6_taps_pruned3.json
python3 $S/merge_identical_types_1026.py die_plan_pd6_f0.json die_plan_pd6_f.json col_h9_r1__t1_pd5_b1_ew col_h9_r1__t1_pd5_fW5_p1_b1 col_h9_r1__t1_pd5_fW5_p2_b1 col_h9_r1__t1_pd5_fE5_p1_b1
python3 $S/regen_explicit_taps_1026.py $W die_plan_pd6_f.json /dev/null $O/pd6_taps_final_check.json --check-only | tail -1
sha256sum die_plan_pd6_f.json
P=$D/die_plan_pd6_f.json; C=$D/die_plan_pd6_composed.json
cd $W
(python3 tools/die_plan/check.py $P --out $O/g0_pd6 --png > $O/g0_pd6.log 2>&1 || true) &
python3 tools/die_plan/gen.py latency "$P" --inplace --out $O/gen_lat_base > $O/gen_lat_base.log 2>&1
python3 tools/die_plan/fallback_regions.py plan "$P" --lat $O/gen_lat_base/s81_latency.json --out $O/regions --block 2 --core tap --hard-merge inputs --groups $W/results/path_s81_pd_1026/scripts/svc_groups.json > $O/regions.log 2>&1
python3 $W/results/fallback_s81_1026/compose_plan.py "$P" $O/regions/landed_crossings.json "$C" $O/side.json > $O/compose.log 2>&1
cat $O/compose.log
python3 tools/die_plan/gen.py latency "$C" --inplace --out $O/gen_lat_composed > $O/gen_lat_composed.log 2>&1
(python3 tools/die_plan/check.py "$C" --out $O/g0_composed --png > $O/g0_composed.log 2>&1 || true) &
python3 tools/die_plan/die_trial.py kit "$C" --out $O/kit --htree-full-depth --leaf-um 300 --tree-site-legal --tree-site-slide --tap-rep-um 405 \
  --region-trees $O/regions/regions.json > $O/kit_build.log 2>&1
tail -3 $O/kit_build.log
python3 $W/results/fallback_s81_2_1026/scripts/render_regions_tree.py "$C" $O/regions/regions.json $O/kit/clock/tree.json $O/kit/tree_regions.png $O/kit/tree_summary.json > $O/render_tree.log 2>&1 || echo RENDER_FAIL
wait
tail -2 $O/g0_pd6.log; tail -2 $O/g0_composed.log
sha256sum $C
echo KIT_DONE $(date)
