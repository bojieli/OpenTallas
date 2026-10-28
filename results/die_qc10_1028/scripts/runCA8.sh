#!/bin/bash
# DIE-QC-10: built-arrival CA recheck on trial8 (rt2 feed): lpo -> ca_spice xing -> proof -> + fork start rows ->
# count_align_plan (fixed start tree = clock tree, CA-OCV-1 hull table/shared, spice) ; no bind/STA here (INFO estimate)
set -u
Q=/srv/opentallas-scratch2/claude/die-qc10-1028; Q9=/srv/opentallas-scratch2/claude/die-qc9-1028; TR=trial8; R=$Q/ca/t8
T=/srv/opentallas-scratch2/claude/wt/die-qc10-1028/tools
CI=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs
PLAN=$CI/event/qc_k2b_phase12.json; MAP=$CI/part_region.json
log(){ echo "t8: $1 $(date)" >> $R/chain.log; }
mkdir -p $R/run; ln -sfn $Q/$TR/clock $R/run/clk
for C in TT FF; do ln -sfn $Q/c8_$C $R/run/out_$C; done
python3 -I $T/s81_head/landed_phase_ocv.py $PLAN $R/run --tools $T/die_plan --out $R/lpo.json > $R/lpo.log 2>&1; log "lpo rc $?"
cd $R && PYTHONPATH=$T/die_plan python3 $Q9/ca/ca_spice.py $R/lpo.json $MAP $R/grp_spice 1.0485 1.0552 --mc 0 > $R/ca.log 2>&1; log "xing rc $?"
python3 -I $Q9/ca/mk_proof.py $R/run $MAP $R/proof > $R/proof.log 2>&1; log "proof rc $?"
python3 -I $Q/est/add_start_rows.py $R/grp_spice_xing_lpo.json $Q/plan/feed_rt2.json $R/xing_start.json $R/tp.txt >> $R/chain.log 2>&1; log "start rows rc $?"
STA="--sta-proof $R/proof --sta-plan $PLAN --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $R/proof/droop_regions.json --sta-core-latency-ff 202.5"
cd $Q/est && python3 -I cap_fixed_tree.py $R/tp.txt $R/xing_start.json $STA --mc-chips 500 --out $R/plan_fixed.json > $R/plan_fixed.log 2>&1; log "plan fixed-start-tree rc $?"
python3 $T/die_plan/count_align_plan.py $R/grp_spice_xing_lpo.json $STA --out $R/plan_minamb.json > $R/plan_minamb.log 2>&1; log "plan planner-tree (no start ports, INFO) rc $?"
log DONE
