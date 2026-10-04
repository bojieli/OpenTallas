#!/bin/bash
# one 8K component job on the VPRM REAL_MEM die (bld_dbg = HEAD sources: aec77a75f datapath + fault observation port)
# usage: run1.sh NAME PLAN_DIR KV_DIR [THREADS]
E=/srv/opentallas-scratch/claude/qwen-dspark-system; C=$E/ctx8k
n=$1; j=$2; kv=$3; th=${4:-6}
echo "$(date -u +%FT%TZ) $n start" >> $C/chain.log
cd $E/src-dbg
/srv/opentallas-scratch/admit.sh 16 -- python3 tools/qwen_rom_rt_vprm_w12.py --workdir $C/runs/$n --build-dir $E/bld_dbg --hbm-layers 3 --code-banks 1 \
  --plan $j/plan --expect $j/expect.json --kv-dir $kv --result $C/res/$n.json --threads $th > $C/runs/$n.out 2>&1
echo $? > $C/runs/$n.rc
echo "$(date -u +%FT%TZ) $n rc=$(cat $C/runs/$n.rc)" >> $C/chain.log
