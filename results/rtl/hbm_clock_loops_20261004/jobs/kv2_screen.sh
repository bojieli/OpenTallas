#!/bin/bash
# KV lifecycle SS screen from src_kv2 with the top-600 reg-to-reg endpoint summary. Usage: kv2_screen.sh <round> <label> <source.sv>
R=/srv/opentallas-scratch/claude/hbm-clock-loops
rnd=$1; lab=$2; src=$3; shift 3
O=$R/runs/$rnd; mkdir -p $O
cd $R/src_kv2
export OT_SCREEN_ROOT=$R/src_kv2
exec /srv/opentallas-scratch/admit.sh ${NEED:-12} -- python3 results/rtl/hbm_clock_loops_20261004/jobs/screen_kv.py --work $O/$lab --output $O/$lab.json --label $lab \
  --source $src --top ot_hbm_accel_kv_lifecycle --param ENABLE=1 --period-ns 0.833 --domain 1.2GHz-SM "$@" > $O/$lab.log 2>&1
