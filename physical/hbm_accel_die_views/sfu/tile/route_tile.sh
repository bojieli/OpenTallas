#!/bin/bash
# fill-8 2026-10-10: harden hfd_sfu_tile (tiled half-width SFU quarter: one CLOSED ot_su12_sfu lane + its register strip;
# tools/hbm_hub_quarter_gen.py --quarter sfu --tiled --half-width).  Every tile pin is a register pin: bc_in / acc_in ->
# posedge pin flops, bc_out / acc_out <- negedge face lockups; the pin flops and lockups are anchored beside their pins
# (common/wire_stage_fence.tcl OT_WS_PINREG / OT_WS_OUTPUT_PINREG).  Lane macro at its tile.json origin (y on the M4
# track lattice).  IO: tile/faced_io.sdc (falling-edge peer launch, 0.2 T budgets), no IO false path; corner STA, the
# 833 ps re-time (tile/signoff833_faced.sdc), then the tile view (LEF + ETMs) for the quarter.
#   route_tile.sh <label> [run_abi3_physical args]   env: OUT, SRC, CORES, NEED, PD, HM, CP, PDN
set -u
lab=$1; shift
V=physical/hbm_accel_die_views/sfu
T=$V/rtl_tiled
L=${LANEDIR:-$V/lane/ot_su12_sfu}
W=$OUT/$lab; mkdir -p $W; cd ${SRCDIR:-${SRC:?}}
read TW TH < <(python3 -c "import json;d=json.load(open('$T/tile/tile.json'));print(d['w_um'],d['h_um'])")
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
echo "tile $TW x $TH PD=${PD:-0.50} HM=${HM:-0.010} CP=${CP:-0.770} $*" > $W/args; cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
export OT_MM_FF_SDC="$V/tile/signoff833_faced.sdc"
/srv/opentallas-scratch/admit.sh ${NEED:-40} -- python3 tools/run_abi3_physical.py --view asap7 --top hfd_sfu_tile \
  --source $T/hfd_sfu_tile.sv --macro-view ot_su12_sfu=$L --macro-place-halo 0.5 0.5 \
  --orfs-var MACRO_PLACEMENT_TCL=/src/$T/tile/macro_place.tcl \
  --clock-port clk --clock-period-ns ${CP:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append $V/tile/faced_io.sdc --stages pnr \
  --die-area 0 0 $TW $TH --core-area 0 0.54 $TW $(python3 -c "print(round($TH-0.54,3))") --routing-layers M2 M7 \
  --orfs-var IO_CONSTRAINTS=/src/$T/tile/io_place.tcl \
  --orfs-var PDN_TCL=/src/${PDN:-physical/hbm_accel_die_views/su/pdn_quarter.tcl} --orfs-var PLACE_DENSITY_LB_ADDON= \
  --place-density ${PD:-0.50} --hold-margin-ns ${HM:-0.010} --orfs-var ADDER_MAP_FILE= \
  --orfs-var "CTS_ARGS=-sink_clustering_enable -repair_clock_nets -apply_ndr none" \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag sft_$lab \
  --orfs-var OT_WS_PINREG=1 --orfs-var OT_WS_OUTPUT_PINREG=1 --orfs-var OT_IO_FILE=/src/$T/tile/io_place.tcl \
  --step-tcl PRE_GLOBAL_PLACE=physical/hbm_accel_die_views/common/wire_stage_fence.tcl \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --macro $L --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/w18/corner_sta.py --macro $L --orfs-dir $W/work/orfs --post-sdc $V/tile/signoff833_faced.sdc --output $W/corner_sta_833.json > $W/corner833.log 2>&1
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name hfd_sfu_tile --out $W/view --macro-view $L --tmp-dir $W/abs_tmp > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
