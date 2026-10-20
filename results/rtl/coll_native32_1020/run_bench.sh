#!/bin/bash
# QW-ORPHANS 10-20: full 8-die gold (unit+production) and mutant benches of the opt-in FAN32/ADD_FAN32 Q caller, Verilator 5.050
set -uo pipefail
cd "$(dirname "$0")/../../.."
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH; verilator --version
O=${1:?outdir}; WHAT=${2:?gold|mut}; mkdir -p "$O"
B="python3 tools/qwen_coll_tp8_native32_bench.py --split --safe-fan32 --native-adder32 --latu 66 --lats 391"
rc=0
if [ "$WHAT" = gold ]; then
  OT_BENCH_J=8 $B --out "$O/unit" > "$O/unit.log" 2>&1; echo "unit rc=$?" | tee -a "$O/summary.txt"
  OT_BENCH_J=8 $B --out "$O/prod" --production > "$O/prod.log" 2>&1; echo "prod rc=$?" | tee -a "$O/summary.txt"
else
  for m in OT_COLL_SPLIT_MUT_LEAD OT_COLL_SPLIT_MUT_EX OT_COLL_SPLIT_MUT_SBANK OT_COLL_SPLIT_MUT_RERR OT_TP8S_MUT_OWNER OT_TP8S_MUT_GATHER; do
    OT_BENCH_J=8 $B --out "$O/$m" --only 'reduce_8w_x16|gather_4w_x4|mixed_8w_x24' --mutant-define $m > "$O/$m.log" 2>&1; r=$?
    echo "$m rc=$r (expect !=0) $(grep -c "COLL_TP8S FAIL mutant=$m" "$O/$m.log")" | tee -a "$O/summary.txt"
  done
fi
