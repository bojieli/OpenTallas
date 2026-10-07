#!/bin/bash
# SAFE softmax tile route (owner 2026-10-06): routed at 730 ps (sign-off 833.333), hold margin HM (default 35 ps),
# IO false-pathed in the route (the tile boundary is register to register; INPUT hold is left to the die-context check,
# the IO is re-timed against the measured insertion by check_io.sh after sign-off).
# usage: OUT=<dir> SRC=<src root> [CORES=16] route_tile.sh <label> <top> '<P=V ...>' [extra run_abi3_physical args, e.g. --pnr-stop-after cts]
set -o pipefail
L=${1:?label}; TOP=${2:?top}; PARS=${3:-}; shift 3
S=${SRC:-.}; O=${OUT:?out}/$L; mkdir -p $O; cd $S
HM=${HM:-0.035}; CORES=${CORES:-16}
SRCS="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv rtl/hdc/v41x/ot_dsrom_su_softmax_add6.sv rtl/hdc/v41x/ot_dsrom_su_softmax_m9.sv rtl/hdc/v41x/ot_dsrom_su_softmax_add.sv rtl/hdc/v41x/ot_dsrom_su_softmax_exp6.sv"
SA=(); for f in $SRCS; do SA+=(--source $f); done
PA=(); for p in $PARS; do PA+=(--param $p); done
echo "$(date -Is) START $(hostname) $TOP $PARS" >> $O/MANIFEST
export OT_ORFS_NUM_CORES=$CORES OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
python3 tools/run_abi3_physical.py --view asap7 --top $TOP "${SA[@]}" "${PA[@]}" \
  --clock-period-ns 0.730 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners BC \
  --io-delay-fraction 0.2 --false-path-from rst_n --stages pnr --core-utilization 35 --place-density 0.55 \
  --hold-margin-ns $HM --max-fanout 32 --slew-margin-percent 30 \
  --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=$CORES \
  --sdc-append physical/dsrom_su_softmax_safe/route_io_false.sdc \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --nickname-tag safe_$L --keep-workdir $O/work --output $O/physical.json --force "$@" > $O/run.log 2>&1
rc=$?
echo "rc=$rc" > $O/exit
if [ $rc -eq 0 ] && [ -z "${CL_STOP_AFTER:-}" ] && [[ " $* " != *"--pnr-stop-after"* ]]; then
  python3 tools/w18/corner_sta.py --orfs-dir $O/work/orfs --post-sdc physical/dsrom_su_softmax_safe/signoff_833.sdc --output $O/corner_sta.json > $O/sta.log 2>&1
  echo "corner_rc=$?" >> $O/exit
  bash physical/dsrom_su_softmax_safe/check_io.sh $O > $O/io_check.log 2>&1; echo "io_rc=$?" >> $O/exit
fi
echo "$(date -Is) END" >> $O/MANIFEST
