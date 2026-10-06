#!/bin/bash
# route_dt.sh <label> [run_abi3_physical args]; env SRC QCV (CTS-only quad view dir) PD HM CTSA PER CORES NEED
# The bank-built HBM attention die tile hfd_attn_tile_b: generator outline / pins, option-B quads + pipeline banks.
A=/srv/opentallas-scratch2/scratch/claude/hbm-attn; lab=$1; shift
W=$A/routes_dt/$lab; mkdir -p $W; cd $A/${SRC:-src_dt}
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
D=physical/hbm_attn_tile_r
echo "SRC=${SRC:-src_dt} QCV=${QCV:-$D/quad_b_cts/ot_attn_tile_m6h1q} CTSA=$CTSA PD=${PD:-0.40} HM=${HM:-0.020} PER=${PER:-0.770} $*" > $W/args; cat SOURCE_COMMIT > $W/SOURCE_COMMIT
/srv/opentallas-scratch/admit.sh ${NEED:-48} -- python3 tools/run_abi3_physical.py --view asap7 --top hfd_attn_tile_b \
  --source rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv --source $D/quad_parent_phys.sv --source $D/quad_bb.sv --source $D/die_tile/bank_bb.sv \
  --macro-view ot_attn_tile_m6h1q=${QCV:-$D/quad_b_cts/ot_attn_tile_m6h1q} \
  --macro-view ot_attn_bank_sn544=$D/bank/ot_attn_bank_sn544 --macro-view ot_attn_bank_ew544=$D/bank/ot_attn_bank_ew544 \
  --macro-place-halo 1 1 \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io --stages pnr \
  --die-area 0 0 1349.112 1349.976 --core-area 0 0 1349.112 1349.976 --place-density ${PD:-0.40} --routing-layers M2 M7 \
  --orfs-var MACRO_PLACEMENT_TCL=/src/$D/die_tile/macro_placement_b.tcl --orfs-var PDN_TCL=/src/$D/die_tile/pdn_dt.tcl \
  --orfs-var IO_CONSTRAINTS=/src/$D/die_tile/io_place.tcl --orfs-var MACRO_ROWS_HALO_X=1 --orfs-var MACRO_ROWS_HALO_Y=1 \
  --orfs-var ADDER_MAP_FILE= --orfs-var "SYNTH_KEEP_MODULES=ot_attn_rp_reg" ${CTSA:+--orfs-var "CTS_ARGS=$CTSA"} "$@" \
  --step-tcl POST_PDN=$D/die_tile/quad_m7_link.tcl \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent ${SLEWM:-60} --hold-margin-ns ${HM:-0.020} --purpose signoff_target --nickname-tag dt_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
M="--macro $D/quad_b/ot_attn_tile_m6h1q --macro $D/bank/ot_attn_bank_sn544 --macro $D/bank/ot_attn_bank_ew544"
python3 tools/w18/corner_sta.py $M --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/w18/corner_sta.py $M --orfs-dir $W/work/orfs --post-sdc $D/signoff_833_int.sdc --output $W/corner_sta_833.json > $W/corner833.log 2>&1
echo "corner833_rc=$?" >> $W/exit
