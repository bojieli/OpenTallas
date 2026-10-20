#!/bin/bash
# KV-TOK 10-19: wait (<= 12 h) for the KV-GEN8 MU die prep kvs14r-06a659135-gen8mub (fallback -gen8mu) on ot-epyc5, then run the
# same three vehicles as launch_g7.sh on it (WSQK, P0, P1).  Bind outputs needed: die_bound.v, port_bind_v2.json, relay_stages.json.
D=/srv/opentallas-scratch/claude/kv-tok/veh; L=/home/ubuntu/scratch/kv-tok/veh; B=/srv/opentallas-scratch/claude/qwen-kvsys
exec >> $L/gen8_waiter.log 2>&1
for i in $(seq 1 144); do
  for SUF in gen8mub gen8mu; do
    R=$B/kvs14r-06a659135-$SUF
    n=$(ssh ot-epyc5 "ls $R/port_bind_v2/die_bound.v $R/port_bind_v2/port_bind_v2.json $R/case_kv/relay_stages.json 2>/dev/null | wc -l" 2>/dev/null)
    if [ "${n:-0}" = 3 ]; then
      sleep 120; echo "$(date +%H:%M) $R prep outputs present -> g8_$SUF/{WSQK,P0,P1}"
      for v in WSQK:128 P0:300 P1:300; do
        /home/ubuntu/bin/ot-run --mem ${v#*:} --threads 16 --dir $D -- bash -lc "ulimit -s unlimited; KVA_VFLAGS='-fno-dfg -fno-inline' bash tools/qwen_layerbench/kva_vehicle.sh ${v%:*} $R $B/wt-kvs14r-06a659135-$SUF g8_$SUF/${v%:*} cases_stk.txt" > $L/g8_${SUF}_${v%:*}.out 2>&1 &
        sleep 3
      done
      wait; echo "$(date +%H:%M) GEN8 vehicles exited"; exit 0
    fi
  done
  sleep 300
done
echo "$(date +%H:%M) no GEN8 prep in 12 h"; exit 1
