#!/bin/bash
# DIE-HEAD-33: Codex plan.sh (codex-head-start-1355, DATA-aware 200 um, model-only dd) on src25m capture sites; main tools.
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/die-head-33-start
R=/srv/opentallas-scratch2/claude/die-head-33/start/leaf
OLD=/srv/opentallas-scratch2/claude/codex-head-start-0828
T=/srv/opentallas-scratch2/claude/codex-head-ca-0840
H=/srv/opentallas-scratch2/claude/head-start-4
python3 "$W/tools/die_plan/count_align_plan.py" "$R/leaf_ocv.json" --corner TT_droop-regions_corelat450,FF_droop-regions_corelat380 --sta-proof "$T/ca2/proof" --sta-plan "$R/capture/plan.json" --sta-clock-cal spice_cell --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions "$T/ca2/proof/droop_regions.json" --sta-core-latency-ff 380 --sta-ca-ring "$H/ca_ring_hd_tile_dh20.json" --sta-clock-cell inv --start-tree clock --start-leaf-origins --start-capture-taps "$R/capture/capture_taps.json" --start-clean width --start-max-hop-um 200 --start-retime-max 64 --start-prev "$R/plan.json" --start-data-delay "$OLD/dd_model_only_200.json" --mc-chips 2000 --out "$R/data_200.json" > "$R/data_200.log" 2>&1
echo D200_DONE
