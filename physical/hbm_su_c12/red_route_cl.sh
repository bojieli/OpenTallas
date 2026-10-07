#!/bin/bash
# red_route_cl.sh <label> <top> <slot|auto> [extra run_abi3_physical args, e.g. $CL_STOP_AFTER]
# Closure-loop route of the SU reducer vehicles (top1024 in the hfd_su_red slot, or slice64 auto die).  Route at
# PER (default 0.730), IO = 0.2T+150 vs vclk at the CALIBRATED mean SS insertion ($CK_SS_MEAN from the loop's
# CTS-only run; the template's planning latency only for the calibrate run itself).  Sign-off: corner_sta at
# 833.333 with signoff_833_io150.sdc (vclk at each corner's measured insertion, -min 0).
# XSDC (optional): a design-intent SDC appended to the route and re-read at sign-off (half rate: red_half_mcp.sdc).
lab=$1; top=$2; mode=$3; shift 3
W=${OUT:?}/$lab; mkdir -p $W
C=${CORES:-16}
export OT_ORFS_NUM_CORES=$C NUM_CORES=$C OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
case $top in *top1024*) T=red_io_vclk_top.sdc ;; *) T=red_io_vclk_slice.sdc ;; esac
IOSDC=physical/hbm_su_c12/$T
if [ -n "${CK_SS_MEAN:-}" ]; then
  IOSDC=physical/hbm_su_c12/cal_${lab}.sdc
  sed "s/^set ot_L .*/set ot_L $CK_SS_MEAN/" physical/hbm_su_c12/$T > $IOSDC
fi
S0="--source rtl/hdc/v41x/phys/ot_hdc_v41x_vec_red_c12_phys.sv --source rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv --source rtl/hdc/ot_hdc_fastfp_lat_c12.sv --source rtl/hdc/ot_hdc_fp32_f12.sv --source rtl/hdc/v41x/ot_dsrom_su_add6.sv --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_fp32_mul_lat.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv --source rtl/hdc/ot_hdc_prefix.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_sfu.sv"
# SRCF: a file listing other sources (e.g. su_full_sources.txt for ot_su12_full)
if [ -n "${SRCF:-}" ]; then S=""; for f in $(cat $SRCF); do S="$S --source $f"; done; else S="$S0"; fi
S="$S ${EXTRA_SOURCES:-}"
if [ "$mode" = slot ]; then
  G="--die-area 0 0 1399.656 218.136 --core-area 1.08 1.08 1398.576 217.08 --orfs-var IO_CONSTRAINTS=/src/physical/hbm_su_c12/red_top_slot_io.tcl --step-tcl POST_IO_PLACEMENT=physical/hbm_su_c12/red_pinflop_place.tcl"
elif [ "$mode" = box ]; then   # DIE="W H": a die-slot outline (pins by the flow), e.g. hfd_su_full 346.008 x 347.736
  read DW DH <<< "${DIE:?}"
  G="--die-area 0 0 $DW $DH --core-area 1.08 1.08 $(python3 -c "print(round($DW-1.08,3), round($DH-1.08,3))")"
else
  G="--core-utilization ${U:-30}"
fi
echo "$top mode=$mode PD=${PD:-0.5} PER=${PER:-0.730} HM=${HM:-0.010} IOSDC=$IOSDC XSDC=${XSDC:-} CK_SS_MEAN=${CK_SS_MEAN:-} C=$C $*" > $W/args
python3 tools/run_abi3_physical.py --view asap7 --top $top $S \
  --clock-period-ns ${PER:-0.730} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $IOSDC ${XSDC:+--sdc-append $XSDC} --stages synth,pnr \
  $G --place-density ${PD:-0.5} --hold-margin-ns ${HM:-0.010} --orfs-var ADDER_MAP_FILE= \
  --orfs-var "SYNTH_KEEP_MODULES=ot_hdc_fp32_mul_f12_l6 ot_hdc_fp32_add_f12_l6x" \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag su_red_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json "$@" > $W/run.log 2>&1
rc=$?; echo "rc=$rc" > $W/exit
case " $* " in *" cts "*|*"stop-after"*) exit $rc ;; esac
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --post-sdc physical/hbm_su_c12/signoff_833_io150.sdc ${XSDC:+--post-sdc $XSDC} --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
exit $rc
