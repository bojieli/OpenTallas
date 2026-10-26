#!/usr/bin/env bash
# S81U-BK: exact bench of the S81-DV bk units behind their V rung.  The UNCHANGED slab benches judge the unit
# (tb_s81ph_sel: transaction compare vs the native ot_hdc_v41x_sel incl. replays and 3 fail-closed cases; tb_s81ph_col:
# frame / per-stack order / DONE / VM image scoreboard + 5 fail-closed modes) through tb_dsdv_bk_wrap (rung schedule
# model, through-traffic and window checks).  Run from the source root.
#   usage: run_bk_bench.sh sel|col <out> <mut 0..4> [variant ...]
#   variants (sel): base thru mir thrumir odd thruodd   (col): gold<seed>[_thru|_mir|_thrumir|_odd|_thruodd] | fault<mode>
#   (odd = +oddwin: odd drain windows, the only stimulus that reaches mutant 3; collector thruodd (1 word a frame) is
#   below the bench's rate match: frame-atomic merges overflow the egress buffer, as +fullrate did)
#   BK_DEFS (env): extra verilator args.  Legacy record (retired transparent drain forwarding, COORD 10-24 18:55):
#     BK_DEFS=+define+OT_DSDV_BK_LEGACY_FWD on RTL whose dsdv_bk_g BK_DRAIN_SINK default is 0 (main before the sink ruling).
#   verdict line: "DSDV_BK_<UNIT> PASS|FAIL mut=<m>" (exit 0 = PASS); a mutant run must print FAIL.
set -u
U=$1; OUT=$2; MUT=$3; shift 3
VARS=${*:-}
B=rtl/dsrom_sys/s81_dv/unit
mkdir -p "$OUT"
rm -rf "$OUT/obj_${U}_m$MUT"
DV="$B/ot_dsdv_vstop.sv $B/bk/dsdv_bk_v.sv $B/bk/test/tb_dsdv_bk_wrap.sv"
M128=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
M256=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
# PL-BK 10-18: LP=1 runs the selector bench on the LANDED parent dsdv_bk_sel_x_lp (bk/lp/, lp.py) instead of dsdv_bk_sel
LPS=""; LPD=""
if [ "${LP:-0}" = 1 ]; then
  LPS="rtl/common/landed_parent/ot_pl_land.sv $B/bk/dsdv_bk_sel_x.sv $B/bk/lp/dsdv_bk_sel_x_lp.sv"; LPD="+define+OT_DSDV_BK_LP"
fi
if [ "$U" = sel ]; then
  [ -n "$VARS" ] || VARS="base thru mir thrumir odd thruodd"
  verilator --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81ph_sel \
    -GSEARCH_PIPE=1 -GMRG_PIPE=1 -GRQPIPE=1 -GPIPE2=1 -GSLAT=4 -GCMP_RETIME=1 -GQIO=1 \
    +define+OT_S81PH_SEL_SAFE +define+OT_S81PH_SEL_FRPR +define+OT_S81PH_SEL_ILD +define+OT_DSDV_BK=$MUT $LPD ${BK_DEFS:-} \
    -Mdir "$OUT/obj_sel_m$MUT" \
    rtl/common/ot_fwd_link_stage.sv rtl/hdc/ot_hdc_prefix.sv $M256 $M128 \
    rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv \
    rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv \
    rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv \
    rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv \
    rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv \
    rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv \
    $DV $B/bk/dsdv_bk_g.sv $B/bk/dsdv_bkcol_leaves.sv $B/bk/dsdv_bksel_c.sv $B/bk/dsdv_bk_sel.sv $LPS $B/bk/dsdv_bk_col.sv rtl/dsrom_sys/s81_ph/ot_s81ph_col.sv rtl/dsrom_sys/s81_ph/ot_s81ph_col_tile.sv \
    rtl/link/ot_fifo_sram_fwft.sv rtl/dsrom_sys/s81_ph/test/tb_s81ph_sel.sv > "$OUT/build_sel_m$MUT.log" 2>&1 \
    || { echo "DSDV_BK_SEL FAIL mut=$MUT (build, $OUT/build_sel_m$MUT.log)"; exit 1; }
  for v in $VARS; do
    case $v in base) pa="";; thru) pa="+thru";; mir) pa="+mir";; thrumir) pa="+thru +mir";; lmap) pa="+lmap=1";; odd) pa="+oddwin";; thruodd) pa="+thru +oddwin";; esac
    "$OUT/obj_sel_m$MUT/Vtb_s81ph_sel" $pa > "$OUT/run_sel_m${MUT}_$v.log" 2>&1 &
  done
  wait
  bad=0
  for v in $VARS; do
    L="$OUT/run_sel_m${MUT}_$v.log"
    r=$(grep -h '^RESULT' "$L" | tail -1); w=$(grep -h '^WRAP_SUMMARY' "$L" | tail -1)
    echo "sel m$MUT $v: $r | $w"
    if ! grep -q '^RESULT PASS' "$L" || grep -q '^FAIL\|^WRAP_ERR' "$L" || ! echo "$w" | grep -q 'errors 0$'; then bad=1; fi
  done
  [ $bad = 0 ] && echo "DSDV_BK_SEL PASS mut=$MUT" || { echo "DSDV_BK_SEL FAIL mut=$MUT"; exit 1; }
else
  [ -n "$VARS" ] || VARS="gold1 gold2_thru gold3_mir gold4_thrumir gold5_odd fault1 fault2 fault3 fault4 fault5"
  verilator --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81ph_col \
    +define+OT_DSDV_BK=$MUT ${BK_DEFS:-} +define+OT_DSDV_BK_COLB +define+OT_S81PH_COLT_RING -Mdir "$OUT/obj_col_m$MUT" \
    rtl/common/ot_fwd_link_stage.sv $M256 $M128 rtl/link/ot_fifo_sram_fwft.sv \
    rtl/dsrom_sys/s81_ph/ot_s81ph_col.sv rtl/dsrom_sys/s81_ph/ot_s81ph_col_tile.sv \
    $DV $B/bk/dsdv_bk_g.sv $B/bk/dsdv_bkcol_leaves.sv $B/bk/dsdv_bk_col.sv rtl/dsrom_sys/s81_ph/test/tb_s81ph_col.sv > "$OUT/build_col_m$MUT.log" 2>&1 \
    || { echo "DSDV_BK_COL FAIL mut=$MUT (build, $OUT/build_col_m$MUT.log)"; exit 1; }
  for v in $VARS; do
    pa=""
    case $v in gold*) s=${v#gold}; s=${s%%_*}; pa="+seed=$s";; fault*) pa="+mode=${v#fault} +lmap=1 +nothrottle";; esac
    case $v in *_odd) pa="$pa +oddwin";; *_thruodd) pa="$pa +thru +oddwin";; *_thrumir) pa="$pa +thru +mir";; *_thru) pa="$pa +thru";; *_mir) pa="$pa +mir";; esac
    "$OUT/obj_col_m$MUT/Vtb_s81ph_col" $pa > "$OUT/run_col_m${MUT}_$v.log" 2>&1 &
  done
  wait
  bad=0
  for v in $VARS; do
    L="$OUT/run_col_m${MUT}_$v.log"
    r=$(grep -h '^RESULT' "$L" | tail -1); w=$(grep -h '^WRAP_SUMMARY' "$L" | tail -1)
    echo "col m$MUT $v: $r | $w"
    if ! grep -q '^RESULT PASS' "$L" || grep -q '^WRAP_ERR' "$L" || ! echo "$w" | grep -q 'errors 0$'; then bad=1; fi
  done
  [ $bad = 0 ] && echo "DSDV_BK_COL PASS mut=$MUT" || { echo "DSDV_BK_COL FAIL mut=$MUT"; exit 1; }
fi
