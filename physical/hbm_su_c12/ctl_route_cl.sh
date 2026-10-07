#!/bin/bash
# ctl_route_cl.sh <label> <top> [extra run_abi3_physical args]: closure-loop route of the SU c12 controller vehicle
# (ot_su12_ctl16c / ot_su12_ctl16h; lane / side / reducer as register stubs, IO false-pathed: an SU-lane-internal
# vehicle).  Route at PER (default 0.770), sign-off 833.333 with signoff_833_fpio.sdc.
lab=$1; top=$2; shift 2
W=${OUT:?}/$lab; mkdir -p $W
C=${CORES:-16}
export OT_ORFS_NUM_CORES=$C NUM_CORES=$C OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
echo "$top PER=${PER:-0.770} UTIL=${UTIL:-26} PD=${PD:-0.55} HM=${HM:-0.010} $*" > $W/args
S="--source rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv --source rtl/hdc/v41x/phys/ot_hdc_v41x_vec_ctl_stubs_c12.sv --source rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_sfu.sv --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_fastfp_lat_c12.sv --source rtl/hdc/ot_hdc_fp32_f12.sv --source rtl/hdc/v41x/ot_dsrom_su_add6.sv --source rtl/hdc/v41x/ot_dsrom_su_f12.sv --source rtl/hdc/v41/ot_hdc_fsqrt_c12.sv --source rtl/hdc/v41/ot_hdc_fsqrt.sv --source rtl/hdc/ot_hdc_prefix.sv --source rtl/hdc/ot_hdc_fp32_mul_lat.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv --source rtl/hdc/ot_hdc_fpu.sv --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv --source rtl/proto/ot_fp32_add_rne_pipe.sv"
python3 tools/run_abi3_physical.py --view asap7 --top $top $S \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io --stages synth,pnr \
  --core-utilization ${UTIL:-26} --place-density ${PD:-0.55} --hold-margin-ns ${HM:-0.010} --orfs-var ADDER_MAP_FILE= \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag su12_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json "$@" > $W/run.log 2>&1
rc=$?; echo "rc=$rc" > $W/exit
case " $* " in *"stop-after"*) exit $rc ;; esac
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --post-sdc physical/hbm_su_c12/signoff_833_fpio.sdc --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
exit $rc
