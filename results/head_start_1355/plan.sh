#!/bin/bash
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/codex-head-start-1355
R=/srv/opentallas-scratch2/claude/codex-head-start-1355
OLD=/srv/opentallas-scratch2/claude/codex-head-start-0828
T=/srv/opentallas-scratch2/claude/codex-head-ca-0840
H=/srv/opentallas-scratch2/claude/head-start-4
M=${1:?hop bound}
python3 "$W/tools/die_plan/count_align_plan.py" "$OLD/hk5_leaf2/leaf_ocv.json" --corner TT_droop-regions_corelat450,FF_droop-regions_corelat380 --sta-proof "$T/ca2/proof" --sta-plan "$OLD/hk5_leaf2/capture/plan.json" --sta-clock-cal spice_cell --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions "$T/ca2/proof/droop_regions.json" --sta-core-latency-ff 380 --sta-ca-ring "$H/ca_ring_hd_tile_dh20.json" --sta-clock-cell inv --start-tree clock --start-leaf-origins --start-capture-taps "$OLD/hk5_leaf2/capture/capture_taps.json" --start-clean width --start-max-hop-um "$M" --start-retime-max 64 --start-prev "$OLD/hk5_leaf2/plan.json" --start-data-delay "$OLD/dd_model_only_200.json" --mc-chips 2000 --out "$R/hk5_data_$M.json" > "$R/hk5_data_$M.log" 2>&1
