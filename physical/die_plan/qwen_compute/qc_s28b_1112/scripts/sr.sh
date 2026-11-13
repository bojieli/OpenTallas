#!/bin/bash
# QC-S28-B B2: STREET-RULE-1 pass-2 legalize (tools da9ad4d161, levers as run6.sh qc_f) on s28 stage1
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-s28b; POR=physical/die_plan/qwen_compute/plan_of_record
cp $W/planq/s28b_stage1.json $W/srcB/$POR/plan_qc99_s28b1.json
rm -rf $W/sr; mkdir -p $W/sr
echo "sr start $(date) tools $(cat $W/srtools/HEAD)" > $W/sr/run.log
cd $W/srcB && nice -n 19 python3 -I $W/srtools/tools/die_plan/street_rule.py legalize $W/srcB/$POR/plan_qc99_s28b1.json \
  --die qwen_compute --repo . --jobs 6 --out-plan $W/sr/plan.json --event $W/sr/event.json --tsv $W/sr/rows.tsv \
  --rs-halving edge_outline --rs-out $W/sr/rs --set add_regs=2 --set pin_reorder=1 --set max_growth_pct=100 --set rs_worse=99 > $W/sr/log.txt 2>&1
echo "SR_RC=$? end $(date)" >> $W/sr/run.log
