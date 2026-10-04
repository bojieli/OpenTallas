#!/bin/bash
# HA4 R5a SS screen (pre-layout + placed repair, jobs/screen.py from hbm-clock-loops) of one clock domain.
# Usage: r5a_screen.sh <label> <clock-port> <period-ns> [extra args]
R=/srv/opentallas-scratch/claude/hbm-accel-r5a-gates
lab=$1; cp=$2; p=$3; shift 3
cd ${SRC:-$R/src}; export OT_SCREEN_ROOT=${SRC:-$R/src}
M=ot_sram_1r1w_512x128_m4_r2c2
/srv/opentallas-scratch/admit.sh ${NEED:-40} -- python3 jobs/screen.py --work $R/runs/$lab --output $R/runs/$lab.json --label $lab \
  --top ot_hbm_accel_expert_fetch_stream_sram \
  --source rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv --source rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo_rf.sv --source rtl/hbm_accel/service/ot_hbm_accel_expert_stream_pc.sv \
  --source rtl/hbm_accel/service/ot_hbm_accel_expert_fetch_stream_sram.sv \
  --source physical/asap7_memory_macros_v2/$M/${M}_bb.v --blackbox $M --macro $M \
  --param ENABLE=1 --clock-port $cp --period-ns $p --false-path-from hrst_n --utilization 30 "$@" > $R/runs/$lab.log 2>&1
echo $? > $R/runs/$lab.exit
