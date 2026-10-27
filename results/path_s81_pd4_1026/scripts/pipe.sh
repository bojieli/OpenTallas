#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/path-s81-pd4-1026/src_b2c
python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/physical/die_plan/s81/merge_phyfit_chunks_1026.py die_plan_pd4_routed.json --base die_plan_pd2_b2_candidate.json --chunks ../place/chunk*.json --out die_plan_pd4_st.json --ledger ../pd4_station_ledger.json
python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/physical/die_plan/s81/apply_bk_tx64_1026.py die_plan_pd4_st.json die_plan_pd4_tx.json ../pd4_bk_tx64.json
cd /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/tools/die_plan && python3 s81_phy_clock_keepouts.py /srv/opentallas-scratch2/claude/path-s81-pd4-1026/src_b2c/die_plan_pd4_tx.json /srv/opentallas-scratch2/claude/path-s81-pd4-1026/src_b2c/die_plan_pd4_phy.json --report /srv/opentallas-scratch2/claude/path-s81-pd4-1026/pd4_phy_density.json --density
cd /srv/opentallas-scratch2/claude/path-s81-pd4-1026/src_b2c
python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/physical/die_plan/s81/regen_explicit_taps_1026.py /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026 die_plan_pd4_phy.json die_plan_pd4.json ../pd4_taps_ledger.json
python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/tools/die_plan/check.py die_plan_pd4.json --out ../g0_pd4 --png > ../g0_pd4.log 2>&1 || true
tail -5 ../g0_pd4.log
sha256sum die_plan_pd4.json
