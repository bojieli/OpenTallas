#!/bin/bash
set -a; . /home/ubuntu/scratch/dkvr/kvr-derive/base/kv_flags.env; set +a
export OT_KV_ASTK_EXPAND=0
W=/home/ubuntu/wt/kvr-derive-1019
B=/home/ubuntu/scratch/dkvr/kvr-derive/base
O=/home/ubuntu/scratch/dkvr/kvr-derive/bind_base
cd $W/tools/qwen_kv_die
/usr/bin/time -v bash $W/tools/qwen_kv_die/kv_port_bind_v2.sh $B/case_kv/die.v $O $B/case_kv/qkd_kv_relays.sv $B/expand.json
echo BIND_RC $?
