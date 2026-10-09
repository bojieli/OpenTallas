#!/bin/bash
# route_dt_cl.sh <label> [run_abi3_physical args]: closure-loop route of the bank-built HBM attention die tile
# hfd_attn_tile_b in an outline from the die generator.  env: OUT, DW / DH (outline), IOP (io_place), MPL (macro
# placement from tools/hbm_attn_die_tile_place.py), PARAMS ("NAME=V ..." stage counts, must match MPL), PD, HM,
# CTSA, PER (route, default 0.770), CORES.  Quads = the closed option-B quad (quad_b, CTS view for the route), banks =
# the closed SN / EW banks; PG <= M7 (the die drops M8 / M9 over the tile).  Sign-off 833 with signoff_833_int.sdc.
lab=$1; shift
W=${OUT:?}/$lab; mkdir -p $W
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
D=physical/hbm_attn_tile_r
P=""; for kv in ${PARAMS:-}; do P="$P --param $kv"; done
echo "DW=$DW DH=$DH IOP=$IOP MPL=$MPL PARAMS=${PARAMS:-} CTSA=${CTSA:-} PD=${PD:-0.40} HM=${HM:-0.020} PER=${PER:-0.770} $*" > $W/args
python3 tools/run_abi3_physical.py --view asap7 --top hfd_attn_tile_b $P \
  --source rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv --source $D/quad_parent_phys.sv --source $D/quad_bb.sv --source $D/die_tile/bank_bb.sv \
  --macro-view ot_attn_tile_m6h1q=$D/quad_b_cts/ot_attn_tile_m6h1q \
  --macro-view ot_attn_bank_sn544=$D/bank/ot_attn_bank_sn544 --macro-view ot_attn_bank_ew544=$D/bank/ot_attn_bank_ew544 \
  --macro-place-halo 1 1 \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io --stages pnr \
  --die-area 0 0 ${DW:?} ${DH:?} --core-area 0 0 $DW $DH --place-density ${PD:-0.40} --routing-layers M2 M7 \
  --orfs-var MACRO_PLACEMENT_TCL=/src/${MPL:?} --orfs-var PDN_TCL=/src/$D/die_tile/pdn_dt.tcl \
  --orfs-var IO_CONSTRAINTS=/src/${IOP:?} --orfs-var MACRO_ROWS_HALO_X=1 --orfs-var MACRO_ROWS_HALO_Y=1 \
  --orfs-var ADDER_MAP_FILE= --orfs-var "SYNTH_KEEP_MODULES=ot_attn_rp_reg" ${CTSA:+--orfs-var "CTS_ARGS=$CTSA"} \
  --step-tcl POST_PDN=$D/die_tile/quad_m7_link.tcl \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent ${SLEWM:-60} --hold-margin-ns ${HM:-0.020} --purpose signoff_target --nickname-tag dt_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json "$@" > $W/run.log 2>&1
rc=$?; echo "rc=$rc" > $W/exit
case " $* " in *"stop-after"*) exit $rc ;; esac
M="--macro $D/quad_b/ot_attn_tile_m6h1q --macro $D/bank/ot_attn_bank_sn544 --macro $D/bank/ot_attn_bank_ew544"
python3 tools/w18/corner_sta.py $M --orfs-dir $W/work/orfs --post-sdc $D/signoff_833_int.sdc --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
exit $rc
