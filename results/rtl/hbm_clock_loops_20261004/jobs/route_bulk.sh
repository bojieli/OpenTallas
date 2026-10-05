#!/bin/bash
# ORFS route of the bulk-copy successor with its SRAM ring macros (SS setup WC + 60 ps, hold WC,BC + 25 ps), then corner STA.
# Usage: route_bulk.sh <label> <LINE_BITS>
R=/srv/opentallas-scratch/claude/hbm-clock-loops
lab=$1; LB=$2
M=ot_sram_1r1w_1024x256_m2_r2c2; MD=physical/asap7_memory_macros/$M
W=$R/routes/$lab; mkdir -p $W
cd $R/src
export OT_ORFS_NUM_CORES=16
/srv/opentallas-scratch/admit.sh ${NEED:-24} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_accel_bulk_copy \
  --source rtl/gpu/ot_gpu_bulk_copy.sv --source rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv --source $MD/${M}_bb.v \
  --param ENABLE=1 --param LINE_BITS=$LB --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 \
  --macro-view $M=$MD --macro-place-halo 5 5 \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr \
  --core-utilization ${UTIL:-30} --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag hcl_$lab \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --macro $MD --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
