#!/bin/bash
set -u
D=/srv/opentallas-scratch/claude/kv-token-pickup-1019
B=/srv/opentallas-scratch/claude/qwen-kvsys
L=/home/ubuntu/artifacts/kv-tok2-1019
exec >> "$L/gen9_waiter.log" 2>&1
for ((i=0;i<144;i++)); do
 for SUF in gen9s; do
  R=$B/kvs14r-7f9501c62-$SUF
  K=$B/wt-kvs14r-7f9501c62-$SUF
  if ssh ot-epyc6 "test -s $R/STATUS.log && grep -q 'PREP FAIL' $R/STATUS.log"; then
   echo "$(date -Is) exact GEN9 strict PREP failed; no vehicle launched"
   exit 3
  fi
  if ssh ot-epyc6 "test -f $D/STAGED && test -s $R/port_bind_v2/die_bound.v && test -s $R/port_bind_v2/port_bind_v2.json && test -s $R/case_kv/relay_stages.json && test -s $R/case_kv/boot_ages.json && test -s $R/relay_check.json"; then
   echo "$(date -Is) GEN9 strict prep inputs available: $R"
   for v in WSQK:128 P0:300 P1:300; do
    /home/ubuntu/bin/ot-run --mem "${v#*:}" --threads 16 --no-spill --dir "$D" -- bash -lc "ulimit -s unlimited; KVA_VFLAGS='-fno-dfg -fno-inline' bash tools/qwen_layerbench/kva_vehicle.sh ${v%:*} $R $K g9_7f9501c62_$SUF/${v%:*} cases_stk.txt" > "$L/g9_${SUF}_${v%:*}.out" 2>&1 &
    sleep 3
   done
   wait
   echo "$(date -Is) GEN9 vehicle clients ended; inspect individual command statuses"
   exit 0
  fi
 done
 sleep 300
done
printf '%s\n' 'No exact GEN9 inputs; no vehicles launched'
exit 1
