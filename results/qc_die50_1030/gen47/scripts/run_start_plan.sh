#!/bin/bash
# usage: run_start_plan.sh PROOF_DIR OUT_NAME [HOP]
set -u
D=/srv/opentallas-scratch2/claude/die-qc-50/gen47; W=/srv/opentallas-scratch2/claude/wt/die-qc-50-gen47
P=$1; N=$2; H=${3:-400}; mkdir -p $D/$N
cd $D
systemd-run --user --scope -q -p MemoryMax=64G python3 -I $D/scripts/start_plan47.py $W $P $W/physical/die_plan/qwen_compute/plan_of_record/plan_qc49.json $D/inputs $D/$N $H > $D/$N/run.log 2>&1
echo "rc=$? $(date)" > $D/$N/status
