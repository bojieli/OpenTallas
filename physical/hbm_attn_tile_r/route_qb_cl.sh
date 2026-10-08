#!/bin/bash
# route_qb_cl.sh <label> [run_abi3_physical args]: closure-loop form of route_qb.sh (option-B quad ot_attn_tile_m6h1q,
# the qb1_bd150 recipe) for the TC re-route of the deleted quad view (TT-VIEWS 2026-10-07).  Runs from the source root,
# env OUT (run dir), no admit (the loop admits).  The leaf view physical/hbm_attn_tile_r/leaf_b/ot_attn_hgrp_m6h1 (LEF +
# SS/FF/TT, from the lb_u45_m6 leaf route whose pins leaf_b froze) is installed by tools/tt_views/ttv_install.sh first.
# Post-step: the quad view (LEF + SS/FF/TT ETM, quad_interface.sdc, leaf TT lib in the TT pass) -> $W/view.
# env: C (q4g12b) DW (514.89) DH (562.95) PD (0.50) HM (0.030) PER (0.770) CORES (16) CTSA (bd150) MCP (1) TPARAM SLEWM (60)
lab=$1; shift
C=${C:-q4g12b}; DW=${DW:-514.89}; DH=${DH:-562.95}
CTSA=${CTSA:--sink_clustering_enable -repair_clock_nets -distance_between_buffers 150}
LEAF=physical/hbm_attn_tile_r/leaf_b/ot_attn_hgrp_m6h1
W=${OUT:?}/$lab; mkdir -p $W
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
echo "TPARAM=$TPARAM CTSA=$CTSA C=$C DW=$DW DH=$DH PD=${PD:-0.50} HM=${HM:-0.030} MCP=${MCP:-1} $*" > $W/args
[ -s $LEAF/ot_attn_hgrp_m6h1_tt.lib ] || { echo "leaf view missing: $LEAF" > $W/run.log; echo "rc=2" > $W/exit; exit 2; }
python3 tools/run_abi3_physical.py --view asap7 --top ot_attn_tile_m6h1q ${TPARAM:+--param $TPARAM} \
  --source rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv --source physical/hbm_fmax_attn_context/ot_attn_tile_m6h1.sv \
  --macro-view ot_attn_hgrp_m6h1=$LEAF --macro-place-halo 5 5 \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io \
  $([ "${MCP:-1}" = 1 ] && echo --sdc-append physical/hbm_attn_tile_r/leaf_reset_mcp.sdc) --stages pnr \
  --die-area 0 0 $DW $DH --core-area 0 0.54 $DW $(python3 -c "print(round($DH-0.54,3))") --place-density ${PD:-0.50} --routing-layers M2 M7 \
  --orfs-var MACRO_PLACEMENT_TCL=/src/physical/hbm_attn_tile_r/macro_placement_$C.tcl \
  --orfs-var PDN_TCL=/src/physical/hbm_attn_tile_r/pdn_q7.tcl --orfs-var IO_CONSTRAINTS=/src/physical/hbm_attn_tile_r/io_${C}.tcl --orfs-var MACRO_ROWS_HALO_X=5 --orfs-var MACRO_ROWS_HALO_Y=5 \
  --orfs-var ADDER_MAP_FILE= --orfs-var "SYNTH_KEEP_MODULES=ot_attn_rp_reg" --orfs-var "CTS_ARGS=$CTSA" "$@" \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl --slew-margin-percent ${SLEWM:-60} --hold-margin-ns ${HM:-0.030} --purpose signoff_target --nickname-tag qb_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --macro $LEAF --orfs-dir $W/work/orfs --post-sdc physical/hbm_attn_tile_r/leaf_reset_mcp.sdc --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/w18/corner_sta.py --macro $LEAF --orfs-dir $W/work/orfs --post-sdc physical/hbm_attn_tile_r/signoff_833_int.sdc --post-sdc physical/hbm_attn_tile_r/leaf_reset_mcp.sdc --output $W/corner_sta_833.json > $W/corner833.log 2>&1
echo "corner833_rc=$?" >> $W/exit
python3 tools/tt_views/view_export.py --orfs-dir $W/work/orfs --name ot_attn_tile_m6h1q --out $W/view --tmp-dir $W/abs_tmp \
  --interface-sdc physical/hbm_attn_tile_r/quad_interface.sdc --macro-view $LEAF --corners ss,ff,tt > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
