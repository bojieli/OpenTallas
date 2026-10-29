#!/bin/bash
# HEAD-START-3 step 2: leaf re-plan on the ROUTED proof (proof_r1), --start-prev leaf_plan4.json, recipe = codex-head-start-0251/final4.sh
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/head-start-3
C=/srv/opentallas-scratch2/claude/codex-head-start-0251
R=/srv/opentallas-scratch2/claude/head-start-3
CAL=${1:-spice_edge}; TAG=${2:-e}; P=${3:-proof_r1}
cd "$W"
python3 tools/s81_head/head_start_capture_sites.py "$C/input/physical/plan.json" "$R/$P/tap_arrivals_TT.json" --out "$R/capture5$TAG" > "$R/capture5$TAG.log" 2>&1
cp -a "$C/input/physical/core_pins" "$R/capture5$TAG/"
python3 tools/die_plan/count_align_plan.py "$C/leaf_ocv2.json" --corner TT_droop-regions_corelat450,FF_droop-regions_corelat380 --sta-proof "$R/$P" --sta-plan "$R/capture5$TAG/plan.json" --sta-clock-cal $CAL --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions "$R/$P/droop_regions.json" --sta-core-latency-ff 380 --sta-ca-ring results/die_head_21_1028/hk4/clock_profile/ca_ring_hd_tile_dh20.json --sta-clock-cell inv2 --start-tree clock --start-leaf-origins --start-capture-taps "$R/capture5$TAG/capture_taps.json" --start-clean width --start-max-hop-um 360 --start-retime-max 64 --start-prev "$C/leaf_plan4.json" --mc-chips 2000 --out "$R/leaf_plan5$TAG.json" > "$R/leaf_plan5$TAG.log" 2>&1
echo done $?
