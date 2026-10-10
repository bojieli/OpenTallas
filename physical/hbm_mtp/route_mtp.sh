#!/bin/bash
# mtp-hbm 2026-10-08: closure-loop route of the HBM-die MTP blocks (standalone DSpark control elements, router top-K,
# fence, and the die block hfd_mtp) on the CURRENT flow: TC route (loop exports OT_ORFS_CORNER_OVERRIDE=TC), IO against
# vclk at the block's calibrated insertion (io_vclk_m_<CK_SS_MEAN>.sdc = 0.2 T + 150 ps die arrival, routed over-
# constrained at 770 ps effective), sign-off 833.333 / 60 ps (signoff_unc60) with rule-H1 FF hold (vclk_corner_true);
# LB=1 adds the consistent die-link budget (physical/common_flow/link_budget_consistent.sdc) for die-boundary blocks.
#   route_mtp.sh <label> <top> [run_abi3_physical args: --source / --param / --macro-view ...] [--pnr-stop-after cts]
# env: OUT (route base), CORES (16), UTIL (40), PD (0.55), HM (0.025), L (vclk insertion ps; default CK_SS_MEAN / 770),
#      STAGES (synth,pnr; pnr for --macro-view jobs: the macro views live in the ORFS image), MACRO (corner_sta --macro dir), SDCX (extra --sdc-append, e.g. a multicycle design-intent SDC), LB (0/1)
set -u
lab=$1; top=$2; shift 2
W=${OUT:?}/$lab; mkdir -p $W
C=${CORES:-16}
export OT_ORFS_NUM_CORES=$C NUM_CORES=$C OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
L=${L:-${CK_SS_MEAN:-770}}
bash physical/hbm_accel_die_views/common/make_io_vclk_margin.sh $L > /dev/null
SDCA=physical/hbm_accel_die_views/common/io_vclk_m_$L.sdc
echo "$top L=$L UTIL=${UTIL:-40} PD=${PD:-0.55} HM=${HM:-0.025} LB=${LB:-0} VT=${OT_MULTI_VT:-rvt} SDCX=${SDCX:-} $*" > $W/args
cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
python3 tools/run_abi3_physical.py --view asap7 --top $top \
  --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $SDCA ${SDCX:+--sdc-append $SDCX} \
  --stages ${STAGES:-synth,pnr} --core-utilization ${UTIL:-40} --place-density ${PD:-0.55} --hold-margin-ns ${HM:-0.025} \
  --orfs-var ADDER_MAP_FILE= \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag mtp_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json "$@" > $W/run.log 2>&1
rc=$?; echo "rc=$rc" > $W/exit
case " $* " in *"stop-after"*) exit $rc ;; esac
P="--post-sdc physical/hbm_accel_die_views/common/signoff_unc60.sdc --post-sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc"
[ "${LB:-0}" = 1 ] && P="$P --post-sdc physical/common_flow/link_budget_consistent.sdc"
[ -n "${SDCX:-}" ] && P="--post-sdc $SDCX $P"
python3 tools/w18/corner_sta.py ${MACRO:+--macro $MACRO} $P --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
exit $rc
