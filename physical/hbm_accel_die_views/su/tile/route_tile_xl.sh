#!/bin/bash
# hbm-forks 2026-10-10: harden hfd_su_tile (tiled su quarter: one closed ot_su12_light lane + its broadcast / capture /
# accumulate registers in a strip beside it).  Every tile pin is a register pin or one XOR level from it (bc_in -> bcq,
# bcq -> bc_out wiring, acc_in -> rotate -> XOR -> acc_out), all rising/falling launch IO budgets are checked; no IO false paths;
# corner STA, then the tile view (LEF + SS / FF ETM) for the quarter.  The negative-edge outputs are real clock-root lockups.
#   route_tile.sh <label> [run_abi3_physical args]   env: OUT, SRC, CORES, NEED, PD, HM, CP, PDN
set -u
lab=$1; shift
V=physical/hbm_accel_die_views/su
T=$V/rtl_tile_xl
W=$OUT/$lab; mkdir -p $W; cd ${SRCDIR:-${SRC:?}}
read TW TH < <(python3 -c "import json;d=json.load(open('$T/tile.json'));print(d['w_um'],d['h_um'])")
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
echo "tile $TW x $TH PD=${PD:-0.55} HM=${HM:-0.010} CP=${CP:-0.770} $*" > $W/args; cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
G=.views/$lab
CAL=0; for arg in "$@"; do [ "$arg" != cts ] || CAL=1; done
python3 tools/hbm_su_tile_io_budget.py --out $G $( [ "$CAL" = 1 ] && echo --calibrate ) || exit 2
cp $G/budget.json $W/budget.json
export OT_MM_FF_SDC="$G/signoff.sdc"
/srv/opentallas-scratch/admit.sh ${NEED:-24} -- python3 tools/run_abi3_physical.py --view asap7 --top hfd_su_tile_xl \
  --source $T/hfd_su_tile_xl.sv --macro-view ot_su12_light=${LANEDIR:-$V/lane_pk2/ot_su12_light} --macro-place-halo 0.5 0.5 \
  --orfs-var MACRO_PLACEMENT_TCL=/src/$T/macro_place.tcl \
  --clock-port clk --clock-period-ns ${CP:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $G/io.sdc --stages pnr \
  --die-area 0 0 $TW $TH --core-area 0 0.54 $TW $(python3 -c "print(round($TH-0.54,3))") --routing-layers M2 M7 \
  --orfs-var IO_CONSTRAINTS=/src/$T/io_place.tcl \
  --orfs-var PDN_TCL=/src/${PDN:-$V/pdn_quarter.tcl} --orfs-var PLACE_DENSITY_LB_ADDON= \
  --place-density ${PD:-0.55} --hold-margin-ns ${HM:-0.010} --orfs-var ADDER_MAP_FILE= \
  --orfs-var "CTS_ARGS=-sink_clustering_enable -repair_clock_nets -apply_ndr none" \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag sut_$lab \
  --orfs-var OT_WS_PINREG=1 --orfs-var OT_WS_INPUT_COMB=1 --orfs-var OT_IO_FILE=/src/$T/io_place.tcl \
  --step-tcl PRE_GLOBAL_PLACE=physical/hbm_accel_die_views/common/wire_stage_fence.tcl \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
route_rc=$?
echo "rc=$route_rc" > $W/exit
[ "$CAL" != 1 ] || exit "$route_rc"
python3 tools/w18/corner_sta.py --macro ${LANEDIR:-$V/lane_pk2/ot_su12_light} --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/w18/corner_sta.py --macro ${LANEDIR:-$V/lane_pk2/ot_su12_light} --orfs-dir $W/work/orfs --post-sdc $G/signoff.sdc --output $W/corner_sta_833.json > $W/corner833.log 2>&1
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name hfd_su_tile_xl --tt --interface-sdc $G/signoff.sdc --out $W/view --macro-view ${LANEDIR:-$V/lane_pk2/ot_su12_light} --tmp-dir $W/abs_tmp > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
