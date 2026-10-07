#!/bin/bash
cd /srv/opentallas/scratch-overflow/claude/qwen-kvmap-prot; mkdir -p logs
b(){ n=$1; shift; ./build.sh b_$n -GPROTECTED=1 "$@" > b_$n.out 2>&1 || { echo "$n build FAIL" >> summary.txt; return; }
  (cd b_$n && ./obj/Vtb_qwen_rt_kv_stream4) > logs/all_$n.log 2>&1; echo "$n all rc=$?" >> summary.txt; }
b p0 -GKV_MAP=0 & b p1 -GKV_MAP=1 & b neg -GKV_MAP=1 -GKV_MAP_PC=0 & wait; echo DONE > DONE
