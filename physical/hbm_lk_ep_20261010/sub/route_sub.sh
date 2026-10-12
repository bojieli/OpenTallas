#!/bin/bash
# el1011-hbm-coll 2026-10-11: ot_lkep_sub hard tile route (hfd_lk_ep rebuild: 3 tiles + cluster glue; physical spec in
# claude-takeover-20261007/el1011-hbm-coll.log).  864 x 643.2 um, the retry macro (nakh64 view) at (86.4, 91.2) R0 with a
# logic ring, every seam pin on the bottom face (pins_sub.tcl), seam pins flopped at their pins (io_flop_at_pins),
# PDN: core M1/M2 rails, M5/M6 stripes, M7 full stripes as the tile PG pins, the macro's M6 PG strapped from M7
# (main 10-11 decision: per-slot exception for the lkep cluster: tile PG M7, cluster straps M8, die top M9 over the slot)
# (pdn_view_hier.tcl); signals M2-M6.  Then corner_sta + the exact-shape view export (LEF + TT/SS/FF).
#   route_sub.sh <label>   env: OUT (dir), CORES, PD (0.5), HM (0.050), MAXWIRE (um, optional), CTSA, RVIEW, IO_ROUTE_SDC, IO_FF_SDC
set -u
lab=$1; shift
D=physical/hbm_lk_ep_20261010/sub
RV=${RVIEW:-physical/hbm_link_retry_pipeline_20261009/view_wpin_nakh64_hm10}
W=${OUT:-/tmp}/$lab; mkdir -p $W; C=${CORES:-8}
export OT_ORFS_NUM_CORES=$C NUM_CORES=$C OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
DW=864; DH=643.2
echo "kind=lkep_sub die=${DW}x${DH} PD=${PD:-0.5} HM=${HM:-0.050} MAXWIRE=${MAXWIRE:-} RVIEW=$RV $*" > $W/args
cat SOURCE_COMMIT > $W/SOURCE_COMMIT 2>/dev/null
GRTH=physical/abi3/v41x_karb_repair_buffer_cap.tcl; if [ -n "${MAXWIRE:-}" ]; then GRTH=$D/grt_drv_maxwire.tcl; elif [ -n "${PK:-}" ]; then GRTH=physical/redesign_ds/coll_split/pin_access_pregrt.tcl; fi
python3 tools/run_abi3_physical.py --view asap7 --top ot_lkep_sub \
  --source rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv --source rtl/hbm_accel/tu/lk_ep_20261010/ot_crc_par.sv \
  --source rtl/hbm_accel/tu/lk_ep_20261010/ot_hbm_lk_ep.sv --source rtl/hbm_accel/tu/lk_ep_20261010/ot_lkep_sub.sv \
  --orfs-var MACRO_PLACEMENT_TCL=/src/$D/macro_sub.tcl \
  --macro-view ot_hbm_link_retry_pipeline=$RV --macro-place-halo 8 8 \
  --clock-port clk --clock-period-ns 0.833 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction .2 --sdc-append physical/hbm_contracts_20261007/screening.sdc \
  --sdc-append physical/hbm_contracts_20261007/reset_rst_n.sdc ${IO_ROUTE_SDC:+--sdc-append $IO_ROUTE_SDC} --stages pnr \
  --die-area 0 0 $DW $DH --core-area 1.08 1.08 $(python3 -c "print(round($DW-1.08,3), round($DH-1.08,3))") \
  --place-density ${PD:-0.5} --routing-layers M2 M6 --max-transition-ns library --max-fanout 32 \
  --orfs-var ADDER_MAP_FILE= --orfs-var "CTS_ARGS=${CTSA:--sink_clustering_enable -sink_clustering_size 30 -sink_clustering_max_diameter 60 -balance_levels -apply_ndr root_only}" \
  --orfs-var PDN_TCL=/src/physical/hbm_accel_die_views/common/pdn_view_hier.tcl --orfs-var "SYNTH_KEEP_MODULES=" \
  --orfs-var DONT_BUFFER_PORTS=1 --orfs-var 'IO_PLACER_H=M4 M6' --orfs-var 'IO_PLACER_V=M3 M5' \
  --orfs-var 'PLACE_PINS_ARGS=-min_distance 4 -min_distance_in_tracks' \
  --step-tcl PRE_IO_PLACEMENT=$D/pins_sub.tcl \
  --step-tcl PRE_GLOBAL_PLACE=physical/qwen_die_masters/io_flop_at_pins.tcl --step-tcl PRE_DETAIL_PLACE=physical/qwen_die_masters/out_flop_release.tcl \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --step-tcl PRE_GLOBAL_ROUTE=$GRTH ${MAXWIRE:+--orfs-var OT_MAXWIRE_UM=$MAXWIRE} ${PK:+--step-tcl POST_DETAIL_ROUTE=physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl --orfs-var OT_PK_FRAC=$PK} ${PKA:+--orfs-var OT_PK_ABOVE_ONLY=$PKA} \
  --slew-margin-percent 20 --hold-margin-ns ${HM:-0.050} --purpose signoff_target --nickname-tag lks_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited "$@" \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
rc=$?; echo "rc=$rc" > $W/exit
case " $* " in *"stop-after"*) exit $rc ;; esac
python3 tools/w18/corner_sta.py --macro $RV --orfs-dir $W/work/orfs ${IO_FF_SDC:+--post-sdc $IO_FF_SDC} --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/tt_views/view_export.py --orfs-dir $W/work/orfs --name ot_lkep_sub --out $W/view --tmp-dir $W/abs_tmp \
  --macro-view $RV --corners ss,ff,tt > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
exit $rc
