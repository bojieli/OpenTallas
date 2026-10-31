#!/bin/bash
# usage: launch.sh TAG MEM [ENV=VAL ...]  -> ot-run on epyc2 of run_prebuild.sh TAG (background; log $A/otrun_TAG.log)
A=/srv/opentallas-scratch2/claude/die-qc-50/gen47A; D=/srv/opentallas-scratch2/claude/wt/die-qc-50-gen47A/results/qc_die50_1030/gen47A/scripts
TAG=$1; MEM=$2; shift 2
cd $A; nohup ssh -o ControlPath=none hub ~/.local/bin/ot-run --hosts epyc2 --mem $MEM --threads 4 --disk 10 --dir $A -- env "$@" bash $D/run_prebuild.sh $TAG ${XARGS:-} > $A/otrun_$TAG.log 2>&1 < /dev/null &
echo launched $TAG
