#!/bin/bash
# PATH-S81-PD5: PD4 pipeline (place.sh + pipe.sh/pipe2.sh/pipe3.sh) on the PD5 routed plan
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/path-s81-pd5-1026; O=/srv/opentallas-scratch2/claude/path-s81-pd5-1026; S=$W/physical/die_plan/s81
cd $O; mkdir -p place
echo START $(date) code $(git -C $W rev-parse --short HEAD)
for c in $(seq 0 15); do python3 $S/place_pd4_slots_1026.py src_b2c/die_plan_pd5_routed.json --report pd5_routes.json --chunk $c --chunks 16 --out place/chunk$c.json > place/chunk$c.log 2>&1 & done
wait
grep -h RESULT place/chunk*.log
cd $O/src_b2c
python3 $S/merge_phyfit_chunks_1026.py die_plan_pd5_routed.json --base die_plan_pd2_b2_candidate.json --chunks ../place/chunk*.json --out die_plan_pd5_st.json --ledger ../pd5_station_ledger.json
python3 $S/apply_bk_tx64_1026.py die_plan_pd5_st.json die_plan_pd5_tx.json ../pd5_bk_tx64.json
(cd $W/tools/die_plan && python3 s81_phy_clock_keepouts.py $O/src_b2c/die_plan_pd5_tx.json $O/src_b2c/die_plan_pd5_phy.json --report $O/pd5_phy_density.json --density)
L0=/srv/opentallas-scratch2/claude/path-s81-taps-1026/taps_ledger.json
python3 $S/prune_ftphy_taps_1026.py $W die_plan_pd5_phy.json die_plan_pd5_pr.json $L0 ../pd5_taps_pruned.json
python3 $S/regen_explicit_taps_1026.py $W die_plan_pd5_pr.json die_plan_pd5_r1.json ../pd5_taps_ledger1.json | tail -2
python3 $S/prune_ftphy_taps_1026.py $W die_plan_pd5_r1.json die_plan_pd5_p2.json $L0,$O/pd5_taps_ledger1.json ../pd5_taps_pruned2.json
python3 $S/regen_explicit_taps_1026.py $W die_plan_pd5_p2.json die_plan_pd5_r2.json ../pd5_taps_ledger2.json | tail -2
python3 $S/prune_ftphy_taps_1026.py $W die_plan_pd5_r2.json die_plan_pd5_f.json $L0,$O/pd5_taps_ledger1.json,$O/pd5_taps_ledger2.json ../pd5_taps_pruned3.json
python3 $S/regen_explicit_taps_1026.py $W die_plan_pd5_f.json /dev/null ../pd5_taps_final_check.json --check-only | tail -1
(cd $W && python3 tools/die_plan/check.py $O/src_b2c/die_plan_pd5_f.json --out $O/g0_pd5 --png > $O/g0_pd5.log 2>&1 || true)
tail -3 $O/g0_pd5.log
sha256sum die_plan_pd5_f.json
echo DONE $(date)
