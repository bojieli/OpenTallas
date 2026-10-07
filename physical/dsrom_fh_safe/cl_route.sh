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
D=rtl/hdc/v41/dspark_fused_head; H=physical/dsrom_fh_quad; L=ot_hdc_v41_fh_sram_lane_hardened
base=(--source rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv --orfs-var SYNTH_HDL_FRONTEND=slang)
for f in rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/proto/ot_fp32_mul_rne_pipe.sv \
  rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
  $D/capture_candidate/ot_hdc_v41_matvec.sv $D/capture_candidate/ot_hdc_v41_fh_ctx.sv; do base+=(--source $f); done
FP="set_false_path -from [get_ports rst_n]"; MC=""; MAC=()
case $V in
 quad) TOP=ot_hdc_v41_fh_quad
  args=("${base[@]}" --source $D/quad/ot_hdc_v41_fh_quad.sv --param QPIN=1 --param RETURN_EXTRA=6
   --macro-view $L=$H/$L --macro-place-halo 2 2 --orfs-var MACRO_PLACEMENT_TCL=/src/$H/macro_place_quad.tcl
   --orfs-var PDN_TCL=/src/$H/pdn_quad.tcl --die-area 0 0 610 560 --core-area 2 2 608 558 --false-path-from gid
   --orfs-var PWR_NETS_VOLTAGES= --orfs-var GND_NETS_VOLTAGES=
   --core-utilization 30 --max-fanout 16)
  MAC=(--macro $H/$L); FP="$FP
set_false_path -from [get_ports gid*]";;
 hquad) TOP=ot_hdc_v41_fh_hquad
  args=("${base[@]}" --source $D/quad/ot_hdc_v41_fh_hquad.sv --param QPIN=1 --param RETURN_EXTRA=6
   --macro-view $L=$H/$L --macro-place-halo 2 2 --orfs-var MACRO_PLACEMENT_TCL=/src/$H/macro_place_hquad.tcl
   --orfs-var PDN_TCL=/src/$H/pdn_quad.tcl --die-area 0 0 470 300 --core-area 2 2 468 298 --false-path-from gid
   --false-path-from hid --core-utilization ${HUTIL:-30} --max-fanout 16 --param LRET=${LRET:-0}
   --orfs-var PWR_NETS_VOLTAGES= --orfs-var GND_NETS_VOLTAGES=)
  MAC=(--macro $H/$L); FP="$FP
set_false_path -from [get_ports {gid* hid}]";;
 ctl) TOP=ot_hdc_v41_fh_ctl
  args=("${base[@]}")
  for f in $D/capture_candidate/ot_hdc_v41_fh_fault_retire.sv $D/capture_candidate/ot_hdc_v41_fh_retire_parent.sv \
    $D/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv $D/capture_candidate/ot_hdc_v41_fh_checked_permission.sv \
    $D/quad/ot_hdc_v41_fh_adec.sv $D/quad/ot_hdc_v41_fh_head_top.sv $D/quad/ot_hdc_v41_fh_ctl.sv; do args+=(--source $f); done
  args+=(--param RETURN_EXTRA=6 --param SAFE=${CTL_SAFE:-1} --param OREG=${CTL_OREG:-0} --die-area 0 0 300 300
   --core-area 2 2 298 298 --core-utilization 30 --max-fanout 16);;
 ep) TOP=ot_hdc_v41_fh_ep_view
  args=(--source rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv --orfs-var SYNTH_HDL_FRONTEND=slang
   --source $D/capture_candidate/ot_hdc_v41_fh_checked_permission.sv --source $D/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv
   --source $D/quad/ot_hdc_v41_fh_ep_view.sv --param FPIPE=${EP_FPIPE:-2} --die-area 0 0 480 480 --core-area 2 2 478 478
   --core-utilization 30 --max-fanout 16 --false-path-from cold_n)
  FP="$FP
set_false_path -from [get_ports cold_n]";;
 top) TOP=ot_hdc_v41_fh_head_top
  args=("${base[@]}")
  for f in $D/capture_candidate/ot_hdc_v41_fh_fault_retire.sv $D/capture_candidate/ot_hdc_v41_fh_retire_parent.sv \
    $D/capture_candidate/ot_hdc_v41_fh_vm_endpoint_ctx.sv $D/capture_candidate/ot_hdc_v41_fh_checked_permission.sv \
    $D/quad/ot_hdc_v41_fh_adec.sv $D/quad/ot_hdc_v41_fh_head_top.sv; do args+=(--source $f); done
  args+=(--param FPIPE=2 --param SAFE=1 --param RETURN_EXTRA=6 --die-area 0 0 560 560 --core-area 2 2 558 558
   --core-utilization 35 --max-fanout 16);;
 elemA|elemB) TOP=ot_dsrom_head_elem; M=ot_rom_4096x274_m8
  if [ $V = elemA ]; then P=(--param LV=8 --param PAD=0 --param JOIN=1 --param ROWS=32); else P=(--param LV=6 --param PAD=2 --param JOIN=0 --param ROWS=128); fi
  args=(--source rtl/v41rom/ot_dsrom_head_elem.sv --source rtl/v41rom/ot_v41_fadd.sv --source rtl/common/ot_prefix.sv
   --source rtl/v41rom/ot_v41_bmul2.sv --source rtl/v41rom/ot_dsrom_bmul3.sv --source physical/asap7_memory_macros/$M/${M}_bb.v
   "${P[@]}" --param IOREG=1 --param SAFE=1 --param CUT=511 --param SPLIT9=1 --core-utilization ${EUTIL:-40} --macro-place-halo 3 3 --max-fanout 32
   --slew-margin-percent 30 --sdc-append physical/abi3/v41_w10_elem_pp_multicycle.sdc --macro-view $M=physical/asap7_memory_macros/$M)
  MAC=(--macro physical/asap7_memory_macros/$M)
  MC="set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]";;
 glue) TOP=ot_dsrom_head_bundle_glue; HG=physical/s81_die_views/hbglue/margin
  args=(--source rtl/s81/ot_dsrom_head_bundle_glue.sv --source rtl/s81/ot_s81_head_min_delay.sv --source rtl/hdc/ot_hdc_delay.sv
   --param USE_MIN_DELAY_CELLS=1 --param MARGIN=2 --param MIN_DEPTH=2 --core-utilization 30 --routing-layers M2 M6
   --step-tcl POST_PDN=$HG/keep.tcl --step-tcl POST_CTS=$HG/keep.tcl --step-tcl POST_GLOBAL_ROUTE=$HG/keep.tcl);;
 *) echo "unknown view $V"; exit 2;;
esac
IMAX=$(echo "($ISS+250)/1000" | bc -l); IMIN=$(echo "($IFF-50)/1000" | bc -l)
OMAX=$(echo "(250-$ISS)/1000" | bc -l); OMIN=$(echo "-($IFF+50)/1000" | bc -l)
# ROUTE_HOLD_IO=ss (r5, 2026-10-07): the implementation flow repairs hold at WC as well as BC with ONE SDC, so the
# FF-derived IO min (IFF-50) made every boundary path a fake WC hold violation (~SS-FF insertion, 200-280 ps):
# hquad r4 11,540 / ctl r4 14,968 / elemB 38,140 flow hold buffers, hquad DPL-0033. With ss the ROUTE IO min uses
# the SS insertion (WC-consistent); the sign-off SDC below keeps the FF model and FF hold goes to the loop hold ECO.
if [ "${ROUTE_HOLD_IO:-ff}" = ss ]; then
 IMIN=$(echo "($ISS-50)/1000" | bc -l); OMIN=$(echo "-($ISS+50)/1000" | bc -l)
fi
G=physical/dsrom_fh_safe/gen; mkdir -p $G
# HALF=1 (SAFE backstop, OWNER 2026-10-07 05:00): the UNCHANGED view on the half-rate generated clock of the fused-head
# domain (die clock / 2 through the domain ICG; registered crossings at the head boundary, built and benched in the
# parent). The view sees a 1,666.666 ps clock: route at 1,460 ps (same 0.876 ratio as 730/833), sign off at 1,666.666.
# No extra multicycle on top of the generated clock (half_ctl_model.json). Throughput priced in the DS ledger.
PSIGN=833.333; PROUTE=0.730
if [ "${HALF:-0}" = 1 ]; then PSIGN=1666.666; PROUTE=1.460; fi
cat > $G/signoff_$V.sdc <<S2
# generated by physical/dsrom_fh_safe/cl_route.sh ($V): insertion SS $ISS / FF $IFF ps
create_clock -name core_clk -period $PSIGN [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -max $(echo "$ISS+250" | bc) -clock core_clk [all_inputs -no_clocks]
set_input_delay -min $(echo "$IFF-50" | bc) -clock core_clk [all_inputs -no_clocks]
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
