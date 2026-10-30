#!/bin/bash
R=/srv/opentallas-scratch2/claude/die-qc36
while docker ps --format "{{.Names}}" | grep -q dqc36-bb1; do sleep 30; done
if [ -s $R/backbone_bb1/backbone_plan.json ]; then
  ~/.local/bin/ot-run --mem 64 --threads 4 --hosts localhost --dir $R -- $R/run_e2_backbone_noaccess.sh > $R/e2.otrun.log 2>&1
else echo "bb1 produced no plan" > $R/e2.otrun.log; fi
