#!/bin/bash
# CLAUDE S81-RERUN: su_swiglu lane (ESUM + IREG, 0c9c4c32a RTL) in the closure loop with its BUDGET-SHEET IO SDCs
# (results/rtl/budgets_20261006/sheets/ot_dsrom_su_swiglu_lane.json; intra-region su hops).  Route at 833.333 ps with
# the sheet's route-mode uncertainty (123 ps = the 770 ps target); sign-off post-SDCs = sheet signoff + FF hold.
# usage: route.sh <label> [extra run_abi3_physical args, e.g. --pnr-stop-after cts]
# env: SRC, OUT, CORES, HM (hold margin, loop default 0.035), BUDGET_SDC / BUDGET_SDC_SIGNOFF / BUDGET_SDC_FF (loop)
set -u
lab=$1; shift
W=$OUT/$lab; V=physical/s81_die_views/swiglu/.sdc_$lab; mkdir -p $W; cd $SRC; mkdir -p $V
cp $BUDGET_SDC $V/route.sdc && cp $BUDGET_SDC_SIGNOFF $V/signoff.sdc
{ echo 'if {[llength [get_libs -quiet *_FF_*]]} {'; cat $BUDGET_SDC_FF; echo '}'; } > $V/ff_guarded.sdc
cp $V/signoff.sdc physical/s81_die_views/swiglu/budget_signoff.sdc; cp $V/ff_guarded.sdc physical/s81_die_views/swiglu/budget_ff_guarded.sdc
echo "lab=$lab HM=${HM:-0.035} $*" > $W/args
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16}
python3 tools/run_abi3_physical.py --view asap7 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.26 --stages synth,pnr \
  --core-utilization 35 --place-density 0.55 --hold-margin-ns ${HM:-0.035} --sdc-append $V/route.sdc \
  --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --orfs-var REMOVE_ABC_BUFFERS=1 \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --top ot_dsrom_su_swiglu_lane --source rtl/hdc/v41x/ot_dsrom_su_swiglu.sv --source rtl/hdc/v41x/ot_dsrom_su_f12.sv \
  --source rtl/hdc/v41x/ot_dsrom_su_add6.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fpu.sv \
  --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv --source rtl/hdc/ot_hdc_sfu.sv --source rtl/hdc/ot_hdc_fastfp.sv \
  --source rtl/hdc/ot_hdc_fastfp_lat_f12.sv --source rtl/hdc/ot_hdc_fp32_f12.sv --source rtl/hdc/ot_hdc_prefix.sv \
  --param LM=5 --param LA=4 --param ROUTED=1 --param IREG=1 --param ESUM=1 \
  --nickname-tag s81swg_$(echo $lab | tr -c "A-Za-z0-9_\n" _) --purpose signoff_target "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --post-sdc $V/signoff.sdc --post-sdc $V/ff_guarded.sdc --orfs-dir $W/work/orfs \
  --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
