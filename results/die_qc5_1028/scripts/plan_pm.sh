#!/bin/bash
# DIE-QC-5: grpPm plan = DIE-QC-4 grpP recipe on the 3-pair merged map: fallback_land table -> compose -> gen.py latency -> G0C
set -u
B=/srv/opentallas-scratch2/claude/die-qc5-1028; Q=/srv/opentallas-scratch2/claude/die-qc4-1028; WQ=/srv/opentallas-scratch2/claude/wt/die-qc4-1028
MT=$Q/main_tools; BASE=$WQ/physical/die_plan/qwen_compute/die_plan.json; P=$B/plan_grpPm
mkdir -p $P/event; cd $P
log(){ echo "plan_pm: $* $(date)" >> $B/chain.log; }
python3 -I $MT/tools/s81_head/fallback_land.py plan $BASE --out $P --granularity map:$B/regions_grpPm.json > plan.log 2>&1; log "table rc $?"
python3 -I $Q/plan_grpP/compose_qc.py $MT $BASE $P/regions_map.json pd > compose.log 2>&1; log "compose rc $?"
for f in $Q/plan_grpP/event/*; do n=$(basename $f); case $n in qc_grpP_event.json|g0c|g0c.log|lat|lat.log) ;; *) ln -sfn $(readlink -f $f) event/$n;; esac; done
cp pd/landed_plan.json event/qc_grpPm_event.json
cd event && python3 -I $MT/tools/die_plan/gen.py latency qc_grpPm_event.json --inplace --out lat > lat.log 2>&1; log "latency rc $?"
python3 -I $MT/tools/die_plan/check.py --completeness qc_grpPm_event.json --out g0c --png > g0c.log 2>&1; log "g0c rc $?"
sha256sum qc_grpPm_event.json >> $B/chain.log
