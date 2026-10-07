#!/bin/bash
# CLAUDE S81-RERUN: ot_meso_fifo W512 D4 (meso_d4_v7 RTL, aec121692 closed source) die view in the calibrated
# closure-loop flow.  usage: route.sh <label> [extra run_abi3_physical args, e.g. --pnr-stop-after cts]
# env: SRC (source tree), OUT (route base), CK_SS_MEAN (calibrated insertion; planning 300 when absent), CORES
set -u
lab=$1; shift
W=$OUT/$lab; mkdir -p $W $SRC/.views/$lab; cd $SRC
physical/s81_die_views/meso/make_sdc.sh ${CK_SS_MEAN:-300} $SRC/.views/$lab/route.sdc
echo "lab=$lab L=${CK_SS_MEAN:-300} $*" > $W/args
export OT_ORFS_NUM_CORES=${CORES:-8} NUM_CORES=${CORES:-8}
python3 tools/run_abi3_physical.py --view asap7 --top ot_meso_fifo --source rtl/common/ot_meso_fifo.sv \
  --param W=512 --param ENABLE=1 --core-utilization 30 --place-density 0.5 --clock-port wclk \
  --clock-period-ns 0.833333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC \
  --hold-corners WC,BC --io-delay-fraction 0.2 --stages synth,pnr --hold-margin-ns 0.030 --orfs-var ADDER_MAP_FILE= \
  --orfs-var SDC_FILE=/src/.views/$lab/route.sdc --step-tcl POST_CTS=physical/s81_die_views/meso/post_cts_vclk.tcl \
  --nickname-tag s81meso_$(echo $lab | tr -c "A-Za-z0-9_\n" _) --purpose signoff_target "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc physical/s81_die_views/common/signoff_unc60.sdc --orfs-dir $W/work/orfs \
  --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
