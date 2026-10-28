#!/bin/bash
# DIE-QC-11: trial10 (rt2 + inverter tree + DME feed centroid) built-arrival CA with START-TREE-1 --start-tree clock
# DIE-QC-13 trial11 (region_stub): main tools 5e316d5fee + region_stub: lpo -> ca_spice -> proof -> plan phase/width -> bind -> die STA (hold-buffers none)
set -u
Q=/srv/opentallas-scratch2/claude/die-qc13-1028; S=/srv/opentallas-scratch2/claude/die-qc11-1028
TR=trial11; R=$Q/ca/t11; mkdir -p $R
T=/srv/opentallas-scratch2/claude/wt/die-qc13-1028/tools; MT=$T/die_plan
CI=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs
PLAN=$CI/event/qc_k2b_phase12.json; MAP=$CI/part_region.json
log(){ echo "t9: $1 $(date)" >> $R/chain.log; }
PR=$R/proof
F="--sta-proof $PR --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
python3 $MT/count_align_bind.py $R/grp_spice_xing_lpo.json --from-ocv --parts ocv --samples 500 $F --start-tree clock --start-clean width --out $R/bind_width.json > $R/bind_width.log 2>&1; log "bind rc $?"
python3 $MT/die_sta_related.py $PR --plan $PLAN --out $R/sta_width --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $R/bind_width.json --count-align-key region > $R/sta_width.log 2>&1; log "sta rc $?"
