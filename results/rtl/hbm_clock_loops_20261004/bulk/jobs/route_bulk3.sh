#!/bin/bash
# ORFS route of the bulk-copy successor (duplicated eligibility/take flags; RING_MACRO=1: even/odd 512x256 macro groups, two-cycle capture) at 1.2 GHz:
# SS setup WC + 60 ps, hold WC,BC + 25 ps, ADDER_MAP off; then corner STA (SS setup / FF hold).
# Usage: route_bulk3.sh <label> <LINE_BITS> [RING_MACRO=1]   env: UTIL (default 25), NEED (GB, default 24), HALO, PD, CAPM (repair_design cap margin %), SRC
R=/srv/opentallas-scratch/claude/hbm-clock-loops
lab=$1; LB=$2; RM=${3:-1}
if [ "$RM" = 1 ]; then M=ot_sram_1r1w_512x256_m1_r2c2; MD=physical/hbm_accel_macros/$M; SDC="--sdc-append rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_mc2.sdc"
else M=ot_sram_1r1w_1024x256_m2_r2c2; MD=physical/asap7_memory_macros/$M; fi
W=$R/routes/$lab; mkdir -p $W
cd $R/${SRC:-src_bulk}
export OT_ORFS_NUM_CORES=${CORES:-16}
/srv/opentallas-scratch/admit.sh ${NEED:-24} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_accel_bulk_copy \
  --source rtl/gpu/ot_gpu_bulk_copy.sv --source rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv --source $MD/${M}_bb.v \
  --param ENABLE=1 --param LINE_BITS=$LB --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 --param RING_MACRO=$RM \
  --macro-view $M=$MD $SDC --macro-place-halo ${HALO:-5} ${HALO:-5} \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io --stages pnr \
  --core-utilization ${UTIL:-25} --place-density ${PD:-0.5} --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= ${CAPM:+--orfs-var CAP_MARGIN=$CAPM} \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag hcl_$lab \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --macro $MD --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
