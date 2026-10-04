#!/bin/bash
# HA4 R5a element route on ot-epyc1tb (ORFS, SS setup WC + 60 ps, hold WC,BC + 25 ps).
# Usage: r5a_route.sh <label> [extra run_abi3_physical args...]; run from the pinned src/ tree.
R=/srv/opentallas-scratch/claude/hbm-accel-r5a-gates
lab=$1; shift
W=$R/routes/$lab; mkdir -p $W
cd $R/src
export OT_ORFS_NUM_CORES=${CORES:-24}
M=ot_sram_1r1w_512x128_m4_r2c2
/srv/opentallas-scratch/admit.sh ${NEED:-120} -- python3 tools/run_abi3_physical_aligned.py --macro-track-gate \
  --view asap7 --top ot_hbm_accel_expert_fetch_stream_sram \
  --source rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv --source rtl/hbm_accel/service/ot_hbm_accel_expert_stream_pc.sv \
  --source rtl/hbm_accel/service/ot_hbm_accel_expert_fetch_stream_sram.sv \
  --source physical/asap7_memory_macros_v2/$M/${M}_bb.v \
  --macro-view $M=physical/asap7_memory_macros_v2/$M --macro-place-halo 3 3 \
  --step-tcl POST_MACRO_PLACE=physical/dsrom_edge_macro_snap.tcl \
  --param ENABLE=1 --clock-port clk --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --sdc-append physical/hbm_accel/r5a_fetch_two_clock.sdc --false-path-from rst_n \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages pnr \
  --core-utilization ${UTIL:-35} --place-density ${PD:-0.55} --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --max-transition-ns 0.32 --purpose signoff_target --nickname-tag r5a_$lab \
  --keep-workdir $W/work --force --output $W/physical.json "$@" > $W/run.log 2>&1
echo $? > $W/exit
