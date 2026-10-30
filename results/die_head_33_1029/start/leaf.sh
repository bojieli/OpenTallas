#!/bin/bash
# DIE-HEAD-33: Codex hk5_leaf2.sh recipe (codex-head-start-0828) steps 1-5 on src25m (a7435da4), main tools (die-head-33-start wt).
# Only input change: capture sites + die plan = src25m (hd_tile start_capture (362.4,354.208)->(518.4,862.944)); clock proof = codex-head-ca-0840/ca2/proof
# (its tap arrivals are bit-identical to the src25m ot_clk GRT readout, 739/739 TT+FF).
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/die-head-33-start
R=/srv/opentallas-scratch2/claude/die-head-33/start/leaf
T=/srv/opentallas-scratch2/claude/codex-head-ca-0840
H=/srv/opentallas-scratch2/claude/head-start-4
SRC=/srv/opentallas-scratch2/claude/die-head-32/src25m/source_plan.json
python3 "$W/tools/s81_head/head_start_leaf_frames.py" "$T/ca2/region_ocv.json" --regions "$T/inputs/regions.json" --out "$R/leaf_ocv.json" > "$R/leaf_ocv.log"
python3 "$W/tools/s81_head/head_start_capture_sites.py" "$SRC" "$T/ca2/proof/tap_arrivals_TT.json" --out "$R/capture" > "$R/capture.log"
python3 "$W/tools/die_plan/count_align_plan.py" "$R/leaf_ocv.json" --corner TT_droop-regions_corelat450,FF_droop-regions_corelat380 --sta-proof "$T/ca2/proof" --sta-plan "$R/capture/plan.json" --sta-clock-cal spice_cell --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions "$T/ca2/proof/droop_regions.json" --sta-core-latency-ff 380 --sta-ca-ring "$H/ca_ring_hd_tile_dh20.json" --sta-clock-cell inv --start-tree clock --start-leaf-origins --start-capture-taps "$R/capture/capture_taps.json" --start-clean width --start-max-hop-um 360 --start-retime-max 64 --mc-chips 2000 --out "$R/plan.json" > "$R/plan.log" 2>&1
python3 "$W/tools/s81_head/head_start_leaf_bind.py" "$R/plan.json" --table "$T/ca2/table.json" --regions "$T/inputs/regions.json" --die "$R/capture/plan.json" --out "$R/bind" > "$R/bind.log"
python3 "$W/tools/die_plan/start_stage_emit.py" emit "$R/bind/bind.json" "$T/ca2/proof" --ctree "$T/fresh/clk" --plan "$R/capture/plan.json" --out "$R/stages" > "$R/stages.log"
echo LEAF_DONE
