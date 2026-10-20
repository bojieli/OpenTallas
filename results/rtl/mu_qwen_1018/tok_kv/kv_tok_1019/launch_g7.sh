#!/bin/bash
# KV-TOK 10-19: KV attention vehicles on the MU KV die GEN7 kvs14r-4db097403-codexmub (DIAGNOSTIC die: strict bind FAIL
# input_unconnected 4 / RELAY_CHECK FAIL; real case exit1) -- first per-pair PV measurement (P0 = WS+ES+pvw_0, P1 = WN+EN+pvw_1)
# and the QK strip on the MU die (WSQK).  Flattened-die selection + leaf hier blocks: tools/qwen_layerbench/kva_vehicle.sh.
D=/srv/opentallas-scratch/claude/kv-tok/veh; R=/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-4db097403-codexmub
K=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub; L=/home/ubuntu/scratch/kv-tok/veh
run() { local v=$1 m=$2
  /home/ubuntu/bin/ot-run --mem $m --threads 16 --dir $D -- bash -lc "ulimit -s unlimited; KVA_VFLAGS='-fno-dfg -fno-inline' bash tools/qwen_layerbench/kva_vehicle.sh $v $R $K g7/$v cases_stk.txt" > $L/g7_$v.out 2>&1 & sleep 3; }
run WSQK 128
run P0 300
run P1 300
wait
echo "ALL DONE $(date -Is)" >> $L/g7_ALL_DONE
