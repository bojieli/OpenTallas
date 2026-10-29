#!/bin/bash
# HEAD-START-4 V1 byte-identity replay: HEAD-START-3 plan5.sh (spice_edge, tag e) on proof_r1 with old/new tools, no --start-data-delay
set -euo pipefail
V=$1; EXTRA=${2:-}; TAG=${3:-$V}
C=/srv/opentallas-scratch2/claude/codex-head-start-0251; R3=/srv/opentallas-scratch2/claude/head-start-3; R=/srv/opentallas-scratch2/claude/head-start-4
S=$R/$V/tools/die_plan
python3 $S/count_align_plan.py "$C/leaf_ocv2.json" --corner TT_droop-regions_corelat450,FF_droop-regions_corelat380 --sta-proof "$R3/proof_r1" --sta-plan "$R3/capture5e/plan.json" --sta-clock-cal spice_edge --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions "$R3/proof_r1/droop_regions.json" --sta-core-latency-ff 380 --sta-ca-ring $R/ca_ring_hd_tile_dh20.json --sta-clock-cell inv2 --start-tree clock --start-leaf-origins --start-capture-taps "$R3/capture5e/capture_taps.json" --start-clean width --start-max-hop-um 360 --start-retime-max 64 --start-prev "$C/leaf_plan4.json" --mc-chips 2000 $EXTRA --out "$R/head_$TAG.json" > "$R/head_$TAG.log" 2>&1
echo HEAD_${TAG}_RC $? $(date)
