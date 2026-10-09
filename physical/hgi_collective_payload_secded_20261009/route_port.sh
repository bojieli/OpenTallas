#!/bin/bash
# route_ps.sh <label> <port|top> [extra args, e.g. $CL_STOP_AFTER]   (cwd = pinned source snapshot; stream hbm-coll-rtl)
# Per-port split of hfd_coll:
#   port: the slice ot_hcoll_port (18 x ot_sram_1r1w_128x256, PDN top M6: pdn_port.tcl, signals M2-M6) at DIEW x DIEH
#         (default 340 x 340), run_abi3_physical as tools/hbm_contracts_physical.py (pin-registered contract blocks),
#         then corner_sta (+ IO_FF_SDC) and the macro view (LEF + SS/FF/TT ETM, tools/tt_views/view_export.py) -> $W/view
#   top : the die master hfd_coll (rtl_ps/hfd_coll.sv: wrapper + core) through common/route_view.sh with MACROS =
#         8 slices from rtl_ps/views/ot_hcoll_port (installed by tools/tt_views/ttv_install.sh from the slice route)
#         + the core's SRAM macros, PDN pdn_top.tcl; corner_sta reads EVERY macro view (route_view.sh reads the first).
# env: OUT, CORES, PD, PER (0.833), HM (0.050), IO_ROUTE_SDC / IO_FF_SDC (port), DIEW/DIEH + PHALO (port outline and
#      macro halo "x y", default 340x340 / "4 4"), route_view.sh env (top)
# coll-fallback 2026-10-08 (all default to the 8-slice behaviour above):
#   SLICE   slice top module, ot_hcoll_port (default) or ot_hcoll_port2 (the 4-slice fallback: 2 ports a slice, 36 SRAMs;
#           rtl/hbm_accel/tu/ot_hcoll_port2.sv is added to the sources)
#   MPT     slice MACRO_PLACEMENT_TCL (e.g. rtl_ps2/macro_rows.tcl: SRAM rows with wide horizontal channels)
#   PINTOP / PINBOT  --pin-region regexes for the top / bottom slice edges (core side / PHY side)
#   TOPDIR  directory of the top's hfd_coll.sv (default rtl_ps; rtl_ps2 for the 4-slice top)
# coll-port 2026-10-08: 340x340 (67% util incl. the 18 SRAMs = 61% of the die) failed GRT-0116 twice: the placer ringed
#      the die edge with macros, so the 2,736 edge pins and the macro q buses crossed macros on M6 alone (the only
#      horizontal layer over an SRAM; M6 53% used, 7,351 of 12,948 overflow gcells, 8,452 H vs 3,593 V). Variants
#      route at ~42% util with wider halos (DIEW/DIEH/PHALO).
set -u
lab=$1; kind=$2; shift 2
D=physical/hbm_accel_die_views/coll/rtl_ps
SRAM=ot_sram_1r1w_128x256_m1_r2c2; SD=physical/asap7_memory_macros/$SRAM
if [ "$kind" = port ]; then
  W=${OUT:?}/$lab; mkdir -p $W
  C=${CORES:-8}; DW=${DIEW:-340}; DH=${DIEH:-340}
  interior_args=()
  if [ "${INTERIOR:-0}" = 1 ]; then
    interior_args=(--step-tcl POST_MACRO_PLACE=$D/interior_macros.tcl
                   --step-tcl PRE_IO_PLACEMENT=$D/interior_pins.tcl
                   --orfs-var 'IO_PLACER_H=M4 M6' --orfs-var 'IO_PLACER_V=M3 M5'
                   --orfs-var 'PLACE_PINS_ARGS=-min_distance 4 -min_distance_in_tracks')
  fi
  if [ "${CAPTURE_ADJACENT:-0}" = 1 ]; then
    interior_args+=(--step-tcl PRE_GLOBAL_PLACE=$D/capture_adjacent_place.tcl)
  fi
  export OT_ORFS_NUM_CORES=$C NUM_CORES=$C OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
  SL=${SLICE:-ot_hcoll_port}; SLSRC=""; [ $SL = ot_hcoll_port2 ] && SLSRC="--source rtl/hbm_accel/tu/ot_hcoll_port2.sv"
  echo "kind=port slice=$SL mpt=${MPT:-} pintop=${PINTOP:-} pinbot=${PINBOT:-} die=${DW}x${DH} halo=${PHALO:-4 4} PD=${PD:-0.5} PER=${PER:-0.833} HM=${HM:-0.050} IO_ROUTE_SDC=${IO_ROUTE_SDC:-} IO_FF_SDC=${IO_FF_SDC:-} $*" > $W/args
  cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
  python3 tools/run_abi3_physical.py --view asap7 \
    ${MPT:+--orfs-var MACRO_PLACEMENT_TCL=/src/$MPT} ${PINTOP:+--pin-region "$PINTOP=top"} ${PINBOT:+--pin-region "$PINBOT=bottom"} \
    --macro-view $SRAM=$SD --macro-place-halo ${PHALO:-4 4} \
    --clock-port clk --clock-period-ns ${PER:-0.833} --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
    --orfs-corner WC --hold-corners WC,BC --io-delay-fraction .2 --sdc-append physical/hbm_contracts_20261007/screening.sdc \
    --sdc-append physical/hbm_contracts_20261007/reset_rst_n.sdc ${IO_ROUTE_SDC:+--sdc-append $IO_ROUTE_SDC} --stages pnr \
    --die-area 0 0 $DW $DH --core-area 1.08 1.08 $(python3 -c "print(round($DW-1.08,3), round($DH-1.08,3))") \
    --place-density ${PD:-0.5} --routing-layers M2 M6 --max-transition-ns library --max-fanout 8 \
    --orfs-var ADDER_MAP_FILE= --orfs-var "CTS_ARGS=-apply_ndr none" --orfs-var PDN_TCL=/src/$D/pdn_port.tcl \
    --orfs-var "SYNTH_KEEP_MODULES=" \
    --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
    --slew-margin-percent 20 --hold-margin-ns ${HM:-0.050} --purpose signoff_target --nickname-tag hcp_$lab \
    --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "${interior_args[@]}" "$@" \
    --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
  rc=$?; echo "rc=$rc" > $W/exit
  case " $* " in *"stop-after"*) exit $rc ;; esac
  python3 tools/w18/corner_sta.py --macro $SD --orfs-dir $W/work/orfs ${IO_FF_SDC:+--post-sdc $IO_FF_SDC} --output $W/corner_sta.json > $W/corner.log 2>&1
  echo "corner_rc=$?" >> $W/exit
  python3 tools/tt_views/view_export.py --orfs-dir $W/work/orfs --name $SL --out $W/view --tmp-dir $W/abs_tmp \
    --macro-view $SD --corners ss,ff,tt > $W/export.log 2>&1
  echo "export_rc=$?" >> $W/exit
  exit $rc
fi
# ---- top: route_view.sh with every macro view read by corner_sta ----
SL=${SLICE:-ot_hcoll_port}; TD=${TOPDIR:-$D}
PV=$D/views/$SL
[ -s $PV/${SL}_tt.lib ] || { mkdir -p ${OUT:?}/$lab; echo "slice view missing: $PV" > $OUT/$lab/run.log; echo "rc=2" > $OUT/$lab/exit; exit 2; }
R=physical/hbm_accel_die_views/common/route_view.sh
sed -e 's#python3 tools/w18/corner_sta.py \${mac1:+--macro \$mac1}#python3 tools/w18/corner_sta.py $(for mv in ${MACROS:-}; do echo -n " --macro ${mv\#*=}"; done)#' $R > $D/.route_view_ps.sh
grep -q 'echo -n " --macro' $D/.route_view_ps.sh || { echo "route_ps.sh: route_view.sh corner_sta line not found" >&2; exit 3; }
export MACROS="$SL=$PV $SRAM=$SD" PDN=$D/pdn_top.tcl HALO=${HALO:-"4 4"}
bash $D/.route_view_ps.sh $lab hfd_coll $TD/hfd_coll.sv "$@"
