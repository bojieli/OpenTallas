#!/bin/bash
# KV-PARAMS3 10-20: no-copy K-tree / lane8 variants vs the closed originals (rtl/test/qwen_kv_die/tb_qkh_nc.sv) on the
# fleet's pinned Verilator 5.050.
#   tools/qwen_kv_die/qkh_nc_bench.sh MODE MUT OUTDIR [plusargs...]   MODE add|prod|lane8|ktree, MUT 0 (expect PASS) or 1..5
#   -> OUTDIR/bench_<MODE>_m<MUT><TAG>.log ; exit 0 iff the PASS line.  TAG=<suffix> names a variant run (e.g. _rand).
set -u
MODE=$1; M=$2; O=$3; shift 3
R=$PWD
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
verilator --version
OBJ="$O/obj_r2_m$M"; mkdir -p "$OBJ"
DEF=""; [ "$M" != 0 ] && DEF="-DKVP3_MUT$M"
if [ ! -x "$OBJ/Vtb_qkh_nc" ]; then
  verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DSYNTHESIS $DEF \
    --top-module tb_qkh_nc -Mdir "$OBJ" \
    "$R/rtl/lib/ot_rst_relay.sv" "$R/rtl/lib/ot_rst_relay_bounded32.sv" "$R/rtl/hdc/ot_hdc_fp32_qkh_ncr.sv" "$R/rtl/hdc/nearhbm/ot_qkh_lane8_nc32c.sv" "$R/rtl/hdc/nearhbm/ot_qkh_subtiles.sv" "$R/rtl/hdc/nearhbm/ot_qkh_subtiles_nc.sv" \
    "$R/rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv" "$R/rtl/hdc/ot_hdc_delay.sv" "$R/rtl/hdc/ot_hdc_fp32_add_lat_nr.sv" \
    "$R/rtl/hdc/ot_hdc_fp32_add_lat_nc.sv" "$R/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$R/rtl/hdc/ot_hdc_fp32_mul_lat.sv" \
    "$R/rtl/hdc/ot_hdc_prefix.sv" "$R/physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv" \
    "$R/results/rtl/kv_qkh_nc_safe32_1020/tb_qkh_nc32c.sv" > "$O/build_m$M.log" 2>&1 || { tail -30 "$O/build_m$M.log"; exit 2; }
fi
L="$O/bench_${MODE}_m$M${TAG:-}.log"
"$OBJ/Vtb_qkh_nc" +mode=$MODE "$@" > "$L" 2>&1
tail -8 "$L"
grep -q "TB_QKH_NC PASS" "$L"
