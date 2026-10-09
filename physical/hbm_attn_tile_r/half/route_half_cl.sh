#!/bin/bash
# route_half_cl.sh <label> [run_abi3_physical args]: closure-loop route of one HALF attention tile (attn-split,
# OWNER 2026-10-08): TOP = hfd_attn_half_lo | hfd_attn_half_hi (rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv), outline
# 1778.52 x DH from tools/hbm_attn_half_tile_place.py (physical/hbm_attn_tile_r/half/<TOP>/{macro_placement,io_place}.tcl,
# every pin on its pin bank).  Same flow as die_tile/route_dt_cl.sh (closed option-B quads + SN / EW banks, PG <= M7,
# SLIVER blockages, sign-off 833 with signoff_833_int.sdc).  env: OUT, TOP, DH, PARAMS, SLIVER (default 12), HALO, PADG,
# PADD, PD, HM, CTSA, PER, CORES.
lab=$1; shift
W=${OUT:?}/$lab; mkdir -p $W
export OT_ORFS_NUM_CORES=${CORES:-16} NUM_CORES=${CORES:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
D=physical/hbm_attn_tile_r
H=$D/half/${TOP:?}
DW=1778.52
POSTPDN=$D/die_tile/quad_m7_link.tcl
SLIVER=${SLIVER-12}
if [ -n "$SLIVER" ]; then
  POSTPDN=$PWD/$W/post_pdn_sliver.tcl; case "$W" in /*) POSTPDN=$W/post_pdn_sliver.tcl ;; esac
  { cat $D/die_tile/quad_m7_link.tcl; echo "set ot_sliver_um $SLIVER"; cat $D/die_tile/sliver_block.tcl; } > $POSTPDN
fi
PADV=""; [ -n "${PADG:-}" ] && PADV="$PADV --orfs-var CELL_PAD_IN_SITES_GLOBAL_PLACEMENT=$PADG"
[ -n "${PADD:-}" ] && PADV="$PADV --orfs-var CELL_PAD_IN_SITES_DETAIL_PLACEMENT=$PADD"
P=""; for kv in ${PARAMS:-}; do P="$P --param $kv"; done
echo "TOP=$TOP DW=$DW DH=$DH PARAMS=${PARAMS:-} HALO=${HALO:-1} SLIVER=$SLIVER PADG=${PADG:-} PADD=${PADD:-} CTSA=${CTSA:-} PD=${PD:-0.40} HM=${HM:-0.020} PER=${PER:-0.770} $*" > $W/args
python3 tools/run_abi3_physical.py --view asap7 --top $TOP $P \
  --source rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv --source rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv \
  --source $D/quad_parent_phys.sv --source $D/quad_bb.sv --source $D/die_tile/bank_bb.sv \
  --macro-view ot_attn_tile_m6h1q=$D/quad_b_cts/ot_attn_tile_m6h1q \
  --macro-view ot_attn_bank_sn544=$D/bank/ot_attn_bank_sn544 --macro-view ot_attn_bank_ew544=$D/bank/ot_attn_bank_ew544 \
  --macro-place-halo 1 1 \
  --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io --stages pnr \
  --die-area 0 0 $DW ${DH:?} --core-area 0 0 $DW $DH --place-density ${PD:-0.40} --routing-layers M2 M7 \
  --orfs-var MACRO_PLACEMENT_TCL=/src/$H/macro_placement.tcl --orfs-var PDN_TCL=/src/$D/die_tile/pdn_dt.tcl \
  --orfs-var IO_CONSTRAINTS=/src/$H/io_place.tcl --orfs-var MACRO_ROWS_HALO_X=${HALO:-1} --orfs-var MACRO_ROWS_HALO_Y=${HALO:-1}$PADV \
  --orfs-var ADDER_MAP_FILE= --orfs-var "SYNTH_KEEP_MODULES=ot_attn_rp_reg" ${CTSA:+--orfs-var "CTS_ARGS=$CTSA"} \
  --step-tcl POST_PDN=$POSTPDN \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --slew-margin-percent ${SLEWM:-60} --hold-margin-ns ${HM:-0.020} --purpose signoff_target --nickname-tag ah_$lab \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json "$@" > $W/run.log 2>&1
rc=$?; echo "rc=$rc" > $W/exit
case " $* " in *"stop-after"*) exit $rc ;; esac
M="--macro $D/quad_b/ot_attn_tile_m6h1q --macro $D/bank/ot_attn_bank_sn544 --macro $D/bank/ot_attn_bank_ew544"
python3 tools/w18/corner_sta.py $M --orfs-dir $W/work/orfs --post-sdc $D/signoff_833_int.sdc --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
exit $rc
