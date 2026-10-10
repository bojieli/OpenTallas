#!/bin/bash
# Closure-loop route of the DS head SAFE views (owner SAFE directive 2026-10-06): routed at 730 ps, signed off at
# 833.333 ps (60/25), hold margin $HM (loop default 35 ps). IO from the loop's calibrated insertion (owner model:
# in max = CK_SS_MEAN + 250, in min = CK_FF_MEAN - 50, out max = 250 - CK_SS_MEAN, out min = -(CK_FF_MEAN + 50)).
# r2 (23:45 PT): --hold-corners WC,BC. With CORNERS=BC alone ORFS reads only the FF libraries (read_liberty.tcl), so
# placement/CTS/route setup repair ran at FF and the SS sign-off saw -200 ps (elemB r1); elements add fadd SPLIT9.
# Usage (from the source root): cl_route.sh <quad|hquad|ctl|ep|top|elemA|elemB|glue> <label> <out dir> [extra run_abi3_physical args,
# e.g. $CL_STOP_AFTER]. Writes <out>/exit (rc=, corner_rc=), <out>/corner_sta.json and <out>/view/ (LEF + SS/FF ETM).
set -o pipefail
V=${1:?view}; LBL=${2:?label}; O=${3:?out}; shift 3
S=$(pwd); mkdir -p "$O"
# A retry must use a new attempt directory: preserve the original failure and logs.
if [ -e "$O/physical.json" ]; then
 echo "existing result preserved: $O/physical.json; use a new attempt directory" >&2
 exit 2
fi
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
export OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
ISS=${CK_SS_MEAN:-500}; IFF=${CK_FF_MEAN:-300}; HMS=${HM:-0.035}
TOP=ot_mtp_p2_ordered_rows; P2SRC=rtl/experimental/mtp_p2_ordered_20261009/ot_mtp_p2_ordered_rows.sv
# drive-0158: P2_CL=1 routes the -cl successor (pin station + accept register; same macros, pins and outline)
if [ "${P2_CL:-0}" = 1 ]; then TOP=ot_mtp_p2_ordered_rows_cl; P2SRC=rtl/experimental/mtp_p2_ordered_20261009/ot_mtp_p2_ordered_rows_cl.sv; fi
M=ot_sram_1r1w_128x256_m1_r2c2
MV=physical/asap7_memory_macros/$M
# mtp-lead 2026-10-09: P2_PATH=1 routes the SELECTED MD-2 P2 line (V22/R7): ot_mtp_p2_prefix_path = PRIMARY_SHARED1
# nine-SRAM ordered transport -> three-SRAM 16-lane LAT8 FP32 A-prefix (+0, E0, E1, E2) -> native 512-b publisher
# (codex/mtp-die-continuation 0091c7ad5 gate PASS 5,467 cycles).  12 real SRAMs on a generic grid
# (macro_place_grid.tcl), outline P2_W x P2_H (default 480 x 400; jobs use 500 x 420 and 560 x 460).
EXTRA=(); MPT=/src/physical/mtp_p2_transport/macro_place.tcl; DW=400; DH=360; PARAMS=(--param ENABLE=1 --param MUT_ORDER=0)
if [ "${P2_PATH:-0}" = 1 ]; then
 TOP=ot_mtp_p2_prefix_path; D=rtl/experimental/mtp_p2_ordered_20261009; P2SRC=$D/ot_mtp_p2_prefix_path.sv
 EXTRA=(--source $D/ot_mtp_p2_ordered_rows.sv --source $D/ot_mtp_p2_prefix.sv --source $D/ot_mtp_p2_prefix_native.sv
        --source rtl/v41rom/ot_v41_fadd.sv --source rtl/common/ot_prefix.sv --source rtl/common/ot_sc_pfifo.sv)
 # (ot_sc_pfifo: REGB=1 pin FIFOs, mtp-lead p2fix 2026-10-09; unused when REGB=0)
 MPT=/src/physical/mtp_p2_transport/macro_place_grid.tcl; DW=${P2_W:-480}; DH=${P2_H:-400}; PARAMS=(--param ENABLE=1 --param ROOTPIPE=${P2_ROOTPIPE:-0})
 if [ "${P2_ROOTPIPE:-0}" = 1 ]; then EXTRA+=(--step-tcl POST_IO_PLACEMENT=physical/mtp_p2_transport/rootpipe_pin_place.tcl); fi
fi
args=(--source $P2SRC "${EXTRA[@]}"
 --source rtl/common/ot_secded.sv --source $MV/${M}_bb.v
 "${PARAMS[@]}" --orfs-var SYNTH_HDL_FRONTEND=slang
 --orfs-var VERILOG_INCLUDE_DIRS=/src/rtl/common
 --macro-view $M=$MV --macro-place-halo 3 3
 --orfs-var MACRO_PLACEMENT_TCL=$MPT
 --die-area 0 0 $DW $DH --core-area 2 2 $((DW-2)) $((DH-2)) --core-utilization 55
 --max-fanout 16 --routing-layers M2 M6
 --orfs-var 'PLACE_PINS_ARGS=-min_distance 4 -min_distance_in_tracks'
 --pin-region "^in_.*=left:20-$((DH-20))" --pin-region "^out_.*=right:20-$((DH-20))"
 --pin-region "^(clk|rst_n|start_.*|sink_abort|abort|done|fault|corrected)\$=top:20-$((DW-20))"
 --pin-regions-exhaustive)
MAC=(--macro $MV); FP="set_false_path -from [get_ports rst_n]"; MC=""
IMAX=$(echo "($ISS+250)/1000" | bc -l); IMIN=$(echo "($IFF-${IN_HOLD_SKEW:-0})/1000" | bc -l)
OMAX=$(echo "(250-$ISS)/1000" | bc -l); OMIN=$(echo "-($IFF+50)/1000" | bc -l)
# RULE H1 (flow-hold 2026-10-07): a die link's 50 ps hold term is carried ONCE, by the sender's output min
# (-(IFF+50)); the receiver's input min is IFF - IN_HOLD_SKEW (default 0; was IFF-50, counted on both sides).
# ROUTE_HOLD_IO=ss (r5, 2026-10-07): the implementation flow repairs hold at WC as well as BC with ONE SDC, so the
# FF-derived IO min (IFF-50) made every boundary path a fake WC hold violation (~SS-FF insertion, 200-280 ps):
# hquad r4 11,540 / ctl r4 14,968 / elemB 38,140 flow hold buffers, hquad DPL-0033. With ss the ROUTE IO min uses
# the SS insertion (WC-consistent; rule H1: input min = ISS - IN_HOLD_SKEW); the sign-off SDC below keeps the FF model and FF hold goes to the loop hold ECO.
if [ "${ROUTE_HOLD_IO:-ff}" = ss ]; then
 IMIN=$(echo "($ISS-${IN_HOLD_SKEW:-0})/1000" | bc -l); OMIN=$(echo "-($ISS+50)/1000" | bc -l)
fi
G=physical/mtp_p2_transport/gen; mkdir -p $G
# HALF=1 (SAFE backstop, OWNER 2026-10-07 05:00): the UNCHANGED view on the half-rate generated clock of the fused-head
# domain (die clock / 2 through the domain ICG; registered crossings at the head boundary, built and benched in the
# parent). The view sees a 1,666.666 ps clock: route at 1,460 ps (same 0.876 ratio as 730/833), sign off at 1,666.666.
# No extra multicycle on top of the generated clock (half_ctl_model.json). Throughput priced in the DS ledger.
PSIGN=833.333; PROUTE=0.770
if [ "${HALF:-0}" = 1 ]; then PSIGN=1666.666; PROUTE=1.460; fi
cat > $G/signoff_$V.sdc <<S2
# generated by physical/dsrom_fh_safe/cl_route.sh ($V): insertion SS $ISS / FF $IFF ps
create_clock -name core_clk -period $PSIGN [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -max $(echo "$ISS+250" | bc) -clock core_clk [all_inputs -no_clocks]
set_input_delay -min $(echo "$IFF-${IN_HOLD_SKEW:-0}" | bc) -clock core_clk [all_inputs -no_clocks]
set_output_delay -max $(echo "250-$ISS" | bc) -clock core_clk [all_outputs]
set_output_delay -min $(echo "-($IFF+50)" | bc) -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
$FP
$MC
S2
echo "$(date -Is) START $(hostname) $V $LBL ins $ISS/$IFF HM $HMS holdio ${ROUTE_HOLD_IO:-ff} period $PSIGN/$PROUTE $*" >> $O/MANIFEST
python3 tools/run_abi3_physical.py --source-root "$S" --view asap7 --top $TOP "${args[@]}" \
 --clock-period-ns $PROUTE --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --stages pnr --false-path-from rst_n \
 --core-input-delay-min-ns $IMIN --core-input-delay-max-ns $IMAX --output-delay-min-ns $OMIN --output-delay-max-ns $OMAX \
 --orfs-var ADDER_MAP_FILE= --place-density 0.55 --orfs-var PLACE_DENSITY_LB_ADDON= --max-transition-ns 0.25 \
 --hold-margin-ns $HMS --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
 --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
 --keep-workdir "$O/work" --nickname-tag $LBL --keep-heavy-artifacts --output "$O/physical.json" "$@" > $O/run.log 2>&1
rc=$?; result_rc=$rc; echo "rc=$rc" > $O/exit
if [ $rc = 0 ] && ! echo "$*" | grep -q -- --pnr-stop-after; then
 python3 tools/w18/corner_sta.py --orfs-dir $O/work/orfs "${MAC[@]}" --post-sdc $G/signoff_$V.sdc --output $O/corner_sta.json > $O/sta.log 2>&1
 corner_rc=$?; echo "corner_rc=$corner_rc" >> $O/exit
 if [ "$corner_rc" -ne 0 ]; then result_rc=$corner_rc; fi
 python3 tools/w18/export_view.py --orfs-dir $O/work/orfs --name $TOP --post-sdc $G/signoff_$V.sdc "${MAC[@]}" --out $O/view > $O/export.log 2>&1
 export_rc=$?; echo "export_rc=$export_rc" >> $O/exit
 if [ "$export_rc" -ne 0 ]; then result_rc=$export_rc; fi
fi
echo "$(date -Is) END $(cat $O/exit | tr '\n' ' ')" >> $O/MANIFEST

exit "$result_rc"
