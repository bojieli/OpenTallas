#!/bin/bash
# qjob.sh <name> <stages> <comp> <partition args...> ; env QROM_* from the caller
set -u
G=/srv/opentallas-scratch/claude/rom-layer-tput-qwen; n=$1; stages=$2; comp=$3; shift 3
export VERILATOR="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
export QWEN_FX=/srv/opentallas-scratch/claude/token-exact
export QWEN_FX_HISTORY=$QWEN_FX/fx/history QWEN_FX_GOLD=$QWEN_FX/gold/tp4_hs/P8191 QWEN_FX_REF=$QWEN_FX/gold/tp4_hs/oracle.json
export PATH=$(dirname $VERILATOR):$PATH QROM_OPTRACE=1 RT_OPTRACE=1
cd $G/src
env | grep '^QROM_' > $G/logs/$n.env
python3 tools/qwen_missing/partition_token.py build --variant part "$@" --comp $comp --build $G/bld/$n --jobs 24 > $G/logs/build_$n.log 2>&1 || { echo "QJOB $n BUILD FAIL"; tail -5 $G/logs/build_$n.log; exit 3; }
python3 tools/qwen_missing/partition_token.py run --variant part "$@" --comp $comp --build $G/bld/$n --work $G/out/$n --stages $stages --threads 24 > $G/logs/run_$n.log 2>&1; rc=$?
echo "QJOB $n run rc=$rc"; python3 -c "
import json,sys
r=json.load(open('$G/out/$n/result.json')); print('QJOB $n', {k:r.get(k) for k in ('exact','stage_cycles','layer_x_mismatches','kv_mismatches','layer_x_checks','kv_checks')})" 2>&1 | tail -1
rm -rf $G/bld/$n/obj_* 2>/dev/null
exit 0
