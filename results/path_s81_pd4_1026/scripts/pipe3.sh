#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/path-s81-pd4-1026/src_b2c
L=/srv/opentallas-scratch2/claude/path-s81-taps-1026/taps_ledger.json,/srv/opentallas-scratch2/claude/path-s81-pd4-1026/pd4_taps_ledger1.json
python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/physical/die_plan/s81/prune_ftphy_taps_1026.py /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026 die_plan_pd4.json die_plan_pd4_p2.json $L ../pd4_taps_pruned2.json
python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/physical/die_plan/s81/regen_explicit_taps_1026.py /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026 die_plan_pd4_p2.json die_plan_pd4_r2.json ../pd4_taps_ledger2.json | tail -2
python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/physical/die_plan/s81/prune_ftphy_taps_1026.py /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026 die_plan_pd4_r2.json die_plan_pd4_f.json $L,/srv/opentallas-scratch2/claude/path-s81-pd4-1026/pd4_taps_ledger2.json ../pd4_taps_pruned3.json
python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/physical/die_plan/s81/regen_explicit_taps_1026.py /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026 die_plan_pd4_f.json /dev/null ../pd4_taps_final_check.json --check-only | tail -1
python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/tools/die_plan/check.py die_plan_pd4_f.json --out ../g0_pd4 --png > ../g0_pd4.log 2>&1 || true
tail -5 ../g0_pd4.log
sha256sum die_plan_pd4_f.json
