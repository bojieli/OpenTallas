#!/bin/bash
# DIE-QC-13 ESTIMATE: START-TREE-1 width/phase plan on a synthetic proof (args: PROOF OUTTAG)
Q=/srv/opentallas-scratch2/claude/die-qc13-1028/ca/t11i; MT=/srv/opentallas-scratch2/claude/die-qc13-1028/invcal/tools/die_plan
PLAN=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/event/qc_k2b_phase12.json
PR=$1; O=$2
F="--sta-proof $PR --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
for M in ${3:-width}; do python3 $MT/count_align_plan.py $Q/grp_spice_xing_lpo.json $F --start-tree clock --start-clean $M --mc-chips 300 --out ${O}_$M.json > ${O}_$M.log 2>&1; echo "$M rc $?"; done
