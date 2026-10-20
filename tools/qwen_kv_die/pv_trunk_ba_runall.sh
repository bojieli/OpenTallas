#!/bin/bash
# KV-PVW 10-19: qkd_pvw_die_tb composition bench set (fleet; from an export of the repo root).  OUT/summary.txt: one line per run.
set -u
O=${1:-out}; mkdir -p "$O"; export JOBS=${JOBS:-8}
run() { n=$1; want=$2; shift 2; ( env "$@" bash tools/qwen_kv_die/pv_trunk_ba_bench.sh "$O/$n" ${M_TM:-0} ${M_FA:-0} "$CT" > "$O/$n.log" 2>&1; r=$?
  if [ $want = PASS ]; then [ $r = 0 ] && v=OK || v=UNEXPECTED; else [ $r != 0 ] && v=OK || v=UNEXPECTED; fi
  echo "$n want=$want rc=$r $v | $(grep -E '^PV_PAIR_TB' "$O/$n.log" | tr '\n' ';' | cut -c1-900)" >> "$O/summary.txt" ) ; }
CT="1 100 300 1000 4097 8192"
run pos_p0_rl19 PASS RL=19 PAIR=0 & run pos_p0_rl95 PASS RL=95 PAIR=0 & run pos_p1_rl95 PASS RL=95 PAIR=1 & wait
CT="1 100"
run mut_age_m1 FAIL RL=95 AGE_ADJ=-1 & run mut_cfg_swap FAIL RL=95 CFG_SWAP=1 & run mut_cfg_swap_p1 FAIL RL=95 PAIR=1 CFG_SWAP=1 & wait
CT="1 100" M_TM=1 run mut_trunk FAIL RL=95 & CT="1 100" M_FA=1 run mut_flag FAIL RL=95 & wait
cat "$O/summary.txt"; ! grep -q UNEXPECTED "$O/summary.txt"
