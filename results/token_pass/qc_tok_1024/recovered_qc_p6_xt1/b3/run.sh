#!/bin/bash
# QC-P6-XT1: QC bind steps on the snapshot $R/src (main 3e05af806 + branch claude/qc-p6-xt1-1023 plan/tools)
# usage: run.sh OUT RECIPE step...   (steps: elab bind verify portbind)
set -u
R=/srv/opentallas-scratch/claude/qc-p6-xt1; OUT=$1; AB=$2; shift 2
T=$R/src/tools/die_plan; P=$R/src/physical/die_plan/qwen_compute
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
export OT_BIND_YOSYS=/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys
mkdir -p $OUT; cd $R
for step in "$@"; do
  /usr/bin/time -v -o $OUT.$step.time python3 $T/bind.py $step $P/die_plan.json --asbuilt $P/bind/$AB --out $OUT --mem 64 > $OUT.$step.log 2>&1; rc=$?
  echo "STEP $step rc=$rc $(grep Elapsed $OUT.$step.time | awk '{print $NF}') $(grep 'Maximum res' $OUT.$step.time | awk '{print $NF}')KB"; tail -4 $OUT.$step.log | cut -c1-900
  [ $rc -ne 0 ] && [ $step = elab ] && exit $rc
done
exit 0
