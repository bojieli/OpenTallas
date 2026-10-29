#!/bin/bash
R=/srv/opentallas-scratch2/claude/die-qc36
while docker ps --format "{{.Names}}" | grep -q dqc36-bb1; do sleep 30; done
[ -s $R/backbone_bb1/joint_clock_reserved.json ] || { echo "no bb1 output" ; exit 1; }
~/.local/bin/ot-run --mem 96 --threads 4 --hosts localhost --dir $R -- $R/run_pa.sh A > $R/paA.otrun.log 2>&1 &
~/.local/bin/ot-run --mem 96 --threads 4 --hosts localhost --dir $R -- $R/run_pa.sh B > $R/paB.otrun.log 2>&1 &
wait
