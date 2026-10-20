#!/bin/bash
# KV-PARAMS4: kt32c_bench.sh MODE MUT OUTDIR [plusargs]  MODE ktree|ktreelk|mul; MUT 0 | 1 (adder high bit) | 7 (mul top) | H (ktree seam)
set -u
MODE=$1; M=$2; O=$3; shift 3
R=$PWD
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
verilator --version
OBJ="$O/obj_kt32c_m$M"; mkdir -p "$OBJ"
DEF=""; [ "$M" = H ] && DEF="-DKVD_HSMUT"; case "$M" in 1|7) DEF="-DKVP3_MUT$M";; esac
if [ ! -x "$OBJ/Vtb_qkh_kt32c" ]; then
  verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DSYNTHESIS $DEF \
    --top-module tb_qkh_kt32c -Mdir "$OBJ" \
    "$R/rtl/lib/ot_rst_relay.sv" "$R/rtl/lib/ot_rst_relay_bounded32.sv" "$R/rtl/hdc/ot_hdc_fp32_qkh_ncr.sv" \
    "$R/rtl/hdc/ot_hdc_fp32_mul_lat_ncr.sv" "$R/rtl/hdc/nearhbm/ot_qkh_ktree_nc32c.sv" "$R/rtl/hdc/nearhbm/ot_qkh_ktree_lk.sv" \
    "$R/rtl/hdc/nearhbm/ot_qkh_subtiles.sv" "$R/rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv" "$R/rtl/hdc/ot_hdc_delay.sv" \
    "$R/rtl/hdc/ot_hdc_fp32_add_lat_nr.sv" "$R/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$R/rtl/hdc/ot_hdc_fp32_mul_lat.sv" \
    "$R/rtl/hdc/ot_hdc_prefix.sv" "$R/physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv" \
    "$R/results/rtl/kv_params4_qkh_1020/tb_qkh_kt32c.sv" > "$O/build_m$M.log" 2>&1 || { tail -30 "$O/build_m$M.log"; exit 2; }
fi
L="$O/bench_${MODE}_m$M${TAG:-}.log"
"$OBJ/Vtb_qkh_kt32c" +mode=$MODE "$@" > "$L" 2>&1
tail -8 "$L"
grep -q "TB_QKH_KT32C PASS" "$L"
