#!/bin/bash
# FLOW-27 11-04: drive one already generated canary run dir on epyc4 from intel2.
# ot-run has no working host list on epyc4 itself, so the client stays on intel2 and pins --hosts epyc4.
# Same three steps as canary.py submit: job.sh (generate), route_canary.sh (flow), canary.py check.
# Usage on intel2: canary_drive_epyc4.sh <run dir on epyc4> <mem GB> <threads> <src snapshot, only for a {src} recipe, else ->
set -u
R=$1; MEM=$2; TH=$3; SRC=${4:--}
OT="$HOME/.local/bin/ot-run --crit --mem $MEM --threads $TH --hosts epyc4 --no-spill"
E="ssh -o ControlPath=none -o ServerAliveInterval=60 epyc4"
$OT --dir "$R" -- bash "$R/job.sh"; echo "DRIVE job rc=$?"
if ! $E "test -f $R/GENERATED"; then echo "DRIVE no GENERATED: no flow run"; exit 3; fi
PREP=":"
if [ "$SRC" != - ]; then RS=$R/gen/runtime_source; H=physical/die_plan/qwen_kvsys/cores/harden
  PREP="mkdir -p $RS/tools $RS/$H && cp -a $SRC/tools/die_plan $RS/tools/ && cp -a $SRC/physical/common_flow $RS/physical/ && cp -a $SRC/$H/eco $RS/$H/ && cp -a $SRC/$H/run_kit_kv.sh $SRC/$H/corners.tcl $SRC/$H/pin_audit_core.py $RS/$H/"
fi
$E "$PREP && cp $R/route.sh $R/gen/route_canary.sh" || echo "DRIVE prep failed"
$OT --dir "$R/gen" -- bash "$R/gen/route_canary.sh"; echo "DRIVE route rc=$?"
$E "python3 -I $R/canary.py check --run $R"; echo "DRIVE check rc=$?"
