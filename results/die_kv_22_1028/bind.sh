#!/bin/bash
# DIE-KV-22: count-align start re-bind on DIE-KV-21 tree c (proofF_c). Recipe = DIE-KV-15 st2.sh fall (PROOF=proofF, phase),
# tools = DIE-KV-20 gate tools (main 6a56d5811). TAG a = repro of record on proofF_fb; b = tree c with --start-prev record; c = tree c plain.
set -u; TAG=$1; P=$2; shift 2
O=/srv/opentallas-scratch2/claude/die-kv-22-1028; R=/srv/opentallas-scratch2/claude/die-kv-15-1028; T=fb_inv_r150
S=/srv/opentallas-scratch2/claude/die-kv-20-1028/main_6a56d5811/tools/die_plan; PL=$R/hm_r26q15c.json; cd $O
STA="--sta-proof $P --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $P/droop_regions.json --sta-core-latency-ff 202.5 --sta-clock-cell inv"
python3 $S/count_align_bind.py $R/ca_$T/${T}_spice_xing_lpo.json --from-ocv --parts ocv $STA --start-tree clock --start-clean phase "$@" --samples 500 --out st_${TAG}_bind_parts.json > st_${TAG}_bind.log 2>&1; echo BIND_${TAG}_RC $? $(date)
