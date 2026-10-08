#!/bin/bash
# route_t.sh <label> <channel um 70|100> <die_w> <die_h> [run_abi3_physical args]; env PD CORES NEED HM
A=/srv/opentallas-scratch2/scratch/claude/hbm-attn; lab=$1; C=$2; DW=$3; DH=$4; shift 4
W=$A/routes_qb/$lab; mkdir -p $W; cd $A/${SRC:-src_qb}
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
echo "SRC=${SRC:-src_qb} TPARAM=$TPARAM CTSA=$CTSA C=$C DW=$DW DH=$DH PD=${PD:-0.50} HM=${HM:-0.010} $*" > $W/args; cat SOURCE_COMMIT > $W/SOURCE_COMMIT
/srv/opentallas-scratch/admit.sh ${NEED:-32} -- python3 tools/run_abi3_physical.py --view asap7 --top ot_attn_tile_m6h1q ${TPARAM:+--param $TPARAM} \
  --source rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv --source physical/hbm_fmax_attn_context/ot_attn_tile_m6h1.sv \
  --macro-view ot_attn_hgrp_m6h1=physical/hbm_attn_tile_r/leaf_b/ot_attn_hgrp_m6h1 --macro-place-halo 5 5 \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io ${MCP:+--sdc-append physical/hbm_attn_tile_r/leaf_reset_mcp.sdc} --stages pnr \
  --die-area 0 0 $DW $DH --core-area 0 0.54 $DW $(python3 -c "print(round($DH-0.54,3))") --place-density ${PD:-0.50} --routing-layers M2 M7 \
  --orfs-var MACRO_PLACEMENT_TCL=/src/physical/hbm_attn_tile_r/macro_placement_$C.tcl \
  --orfs-var PDN_TCL=/src/physical/hbm_attn_tile_r/pdn_q7.tcl --orfs-var IO_CONSTRAINTS=/src/physical/hbm_attn_tile_r/io_${C}.tcl --orfs-var MACRO_ROWS_HALO_X=5 --orfs-var MACRO_ROWS_HALO_Y=5 \
  --orfs-var ADDER_MAP_FILE= --orfs-var "SYNTH_KEEP_MODULES=ot_attn_rp_reg" ${CTSA:+--orfs-var "CTS_ARGS=$CTSA"} "$@" \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl --slew-margin-percent ${SLEWM:-60} --hold-margin-ns ${HM:-0.010} --purpose signoff_target --nickname-tag qb_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --macro physical/hbm_attn_tile_r/leaf_b/ot_attn_hgrp_m6h1 --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/w18/corner_sta.py --macro physical/hbm_attn_tile_r/leaf_b/ot_attn_hgrp_m6h1 --orfs-dir $W/work/orfs --post-sdc physical/hbm_attn_tile_r/signoff_833_int.sdc --output $W/corner_sta_833.json > $W/corner833.log 2>&1
echo "corner833_rc=$?" >> $W/exit
