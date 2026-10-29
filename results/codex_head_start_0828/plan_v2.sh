#!/bin/bash
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/codex-head-start-0828
R=/srv/opentallas-scratch2/claude/codex-head-start-0828
C=/srv/opentallas-scratch2/claude/codex-head-start-0251
R3=/srv/opentallas-scratch2/claude/head-start-3
H=/srv/opentallas-scratch2/claude/head-start-4
python3 "$W/tools/die_plan/count_align_plan.py" "$C/leaf_ocv2.json" --corner TT_droop-regions_corelat450,FF_droop-regions_corelat380 --sta-proof "$R/proof_components" --sta-plan "$R3/capture5e/plan.json" --sta-clock-cal spice_cell --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions "$R/proof_components/droop_regions.json" --sta-core-latency-ff 380 --sta-ca-ring "$H/ca_ring_hd_tile_dh20.json" --sta-clock-cell inv2 --start-tree clock --start-leaf-origins --start-capture-taps "$R3/capture5e/capture_taps.json" --start-clean width --start-max-hop-um "${1:-200}" --start-retime-max 64 --start-prev "$C/leaf_plan4.json" --start-data-delay "$R/dd_corners_${1:-200}.json" --mc-chips 2000 --out "$R/plan_corner_model_${1:-200}.json" > "$R/plan_corner_model_${1:-200}.log" 2>&1
