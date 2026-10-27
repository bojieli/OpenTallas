#!/bin/bash
set -u
cd /srv/opentallas-scratch2/claude/path-s81-pd4-1026; mkdir -p place
for c in $(seq 0 15); do python3 /srv/opentallas-scratch2/claude/wt/path-s81-pd4-1026/physical/die_plan/s81/place_pd4_slots_1026.py src_b2c/die_plan_pd4_routed.json --report pd4_routes.json --chunk $c --chunks 16 --out place/chunk$c.json > place/chunk$c.log 2>&1 & done
wait
grep -h RESULT place/chunk*.log
