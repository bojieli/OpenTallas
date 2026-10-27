#!/bin/bash
# PATH-S81-PD7 (d = ALL 10 band core-shift types incl gunit/svc_0/svc_7 + ft_nudge re-site of the FT stations the shift put on macros):
# PD5 plan (die_plan_pd5_tx.json) -> band core shifts -> ft_nudge -> PHY density taps -> tap prune/regen (as pipe6c) -> merge b1 frames -> G0
# -> (only if G0 errors <= 13) regions -> compose -> latency -> G0 composed -> kit -> render
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/path-s81-pd7-1026; O=/srv/opentallas-scratch2/claude/path-s81-pd7-1026/d; P5=/srv/opentallas-scratch2/claude/path-s81-pd5-1026
S=$W/physical/die_plan/s81; D=$O/src; mkdir -p $D; for x in $(ls $P5/src_b2c | grep -v ^die_plan_pd); do ln -sfn $P5/src_b2c/$x $D/$x; done; cd $D
echo START $(date) code $(git -C $W rev-parse --short HEAD)
python3 $S/apply_band_core_shift_1026.py $P5/src_b2c/die_plan_pd5_tx.json die_plan_pd7_sh0.json $W/results/path_s81_pd7_1026/bands/shift_base_d.json $O/shift_ledger_d.json
python3 $W/tools/die_plan/ft_nudge.py die_plan_pd7_sh0.json die_plan_pd7_sh.json $O/ft_nudge_ledger.json | tail -3
(cd $W/tools/die_plan && python3 s81_phy_clock_keepouts.py $D/die_plan_pd7_sh.json $D/die_plan_pd7_phy.json --report $O/pd7_phy_density.json --density)
L0=/srv/opentallas-scratch2/claude/path-s81-taps-1026/taps_ledger.json
python3 $S/prune_ftphy_taps_1026.py $W die_plan_pd7_phy.json die_plan_pd7_pr.json $L0 $O/pd7_taps_pruned.json
python3 $S/regen_explicit_taps_1026.py $W die_plan_pd7_pr.json die_plan_pd7_r1.json $O/pd7_taps_ledger1.json | tail -2
python3 $S/prune_ftphy_taps_1026.py $W die_plan_pd7_r1.json die_plan_pd7_p2.json $L0,$O/pd7_taps_ledger1.json $O/pd7_taps_pruned2.json
python3 $S/regen_explicit_taps_1026.py $W die_plan_pd7_p2.json die_plan_pd7_r2.json $O/pd7_taps_ledger2.json | tail -2
python3 $S/prune_ftphy_taps_1026.py $W die_plan_pd7_r2.json die_plan_pd7_f0.json $L0,$O/pd7_taps_ledger1.json,$O/pd7_taps_ledger2.json $O/pd7_taps_pruned3.json
python3 $S/merge_identical_types_1026.py die_plan_pd7_f0.json die_plan_pd7_f.json col_h9_r1__t1_pd5_b1_ew col_h9_r1__t1_pd5_fW5_p1_b1 col_h9_r1__t1_pd5_fW5_p2_b1 col_h9_r1__t1_pd5_fE5_p1_b1
python3 $S/regen_explicit_taps_1026.py $W die_plan_pd7_f.json /dev/null $O/pd7_taps_final_check.json --check-only | tail -1
sha256sum die_plan_pd7_f.json
P=$D/die_plan_pd7_f.json; C=$D/die_plan_pd7_composed.json
cd $W
python3 tools/die_plan/check.py $P --out $O/g0_pd7 --png > $O/g0_pd7.log 2>&1 || true
tail -1 $O/g0_pd7.log
NE=$(grep -o "G0 FAIL: [0-9]* errors" $O/g0_pd7.log | grep -o "[0-9]*" || echo 0)
echo G0_ERRORS $NE
if [ "$NE" -gt 13 ]; then echo "STOP G0 $NE > 13"; exit 3; fi
python3 tools/die_plan/gen.py latency "$P" --inplace --out $O/gen_lat_base > $O/gen_lat_base.log 2>&1
python3 tools/die_plan/fallback_regions.py plan "$P" --lat $O/gen_lat_base/s81_latency.json --out $O/regions --block 2 --core tap --hard-merge inputs --groups $W/results/path_s81_pd_1026/scripts/svc_groups.json > $O/regions.log 2>&1
python3 $W/results/fallback_s81_1026/compose_plan.py "$P" $O/regions/landed_crossings.json "$C" $O/side.json > $O/compose.log 2>&1
cat $O/compose.log
python3 tools/die_plan/gen.py latency "$C" --inplace --out $O/gen_lat_composed > $O/gen_lat_composed.log 2>&1
(python3 tools/die_plan/check.py "$C" --out $O/g0_composed --png > $O/g0_composed.log 2>&1 || true) &
python3 tools/die_plan/die_trial.py kit "$C" --out $O/kit --htree-full-depth --leaf-um 300 --tree-site-legal --tree-site-slide --tap-rep-um 405 \
  --region-trees $O/regions/regions.json > $O/kit_build.log 2>&1
tail -3 $O/kit_build.log
wait
tail -2 $O/g0_composed.log
sha256sum $C
echo KIT_DONE $(date)
