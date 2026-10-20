#!/bin/bash
# KV-KITS-ATTN 2026-10-18: kit bench of qkd_pv_fin_s at the die's parameters (kv_static_die qkd_pvfin: ADD_LAT 7, MUL_LAT 6,
# SKEW 1), Verilator 5.050 (the closure daemon's pinned tool).  tb_qkd_pv_fin_s32 = lockstep against the reference
# ot_qwen_tp8_pv_join16_static_cal slices (bit-exact blocks, beat b = reference + 1 + b), QXF-FACE b6d08acc2 version.
#   run_qkd_pv_fin_s_kit.sh OUT M
#   M=0: lockstep R <= max(P0, P1) (+N=40) AND the die's STRETCH=1 regimes (+N=48) AND the 3 negative controls (DUT fault)
#        -> one line "PVFIN_KIT PASS mut=0 ..." only if all five pass
#   M=1: reciprocal head index (b + 1) / 8        M=2: pair-0 operand one tap late       M=3: R left out of the join age
#        -> the RTL mutant on the stretched lockstep; "PVFIN_KIT FAIL mut=M ..." when the bench catches it
# Exit 0 only on a PVFIN_KIT PASS line.  Run from the repository root (on the fleet via ot-run).
set -u
O=$1; M=${2:-0}
mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=verilator
S=rtl/qwen_sys/split_20261014
SRC=(results/rtl/kv_pvfin_shipping_1020/r10_gold.sv "$S/qkd_pv_fin_s32.sv" rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static_cal_gen.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
     rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_qkd_pvfin_calendar_value.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_qkh_ncr.sv rtl/hdc/ot_hdc_fp32_mul_lat_ncr.sv rtl/hdc/ot_hdc_fp32_mul_lat_pvfin.sv rtl/lib/ot_rst_relay_bounded32.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_pvfin/ot_sram_1r1w_32x128_m1_p192_pvfin.v rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv results/rtl/kv_pvfin_shipping_1020/tb_earliest_start.sv)
sha256sum "${SRC[@]}" "$0" > "$O/source.sha256"
echo "SIM $($V --version)"
$V --binary --timing --x-initial unique --x-assign unique -DOT_MEM_NO_INIT -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN \
   --top-module tb_qkd_pv_fin_s32 -GMUT="$M" -GSKEW=1 --Mdir "$O/obj" "${SRC[@]}" > "$O/build.log" 2>&1 \
   || { grep -m5 %Error "$O/build.log"; echo "PVFIN_KIT FAIL mut=$M build"; exit 1; }
B=$O/obj/Vtb_qkd_pv_fin_s32
rc=0
for stretch in 0 1; do
 "$B" +verilator+rand+reset+2 +verilator+seed+17 +BOOT_WAIT=4 +SEED=9 +N=3 +STRETCH=$stretch >"$O/legal_s$stretch.log" 2>&1 || rc=1
 grep -q "^PASS STRETCH=$stretch 3 commands" "$O/legal_s$stretch.log" || rc=1
done
"$B" +verilator+rand+reset+2 +verilator+seed+17 +BOOT_WAIT=3 +SEED=9 +N=3 >"$O/early_control.log" 2>&1
! grep -q '^PASS STRETCH=0 3 commands' "$O/early_control.log" || rc=1
grep -Eq 'FAIL|fault' "$O/early_control.log" || rc=1
test "$rc" = 0 && echo 'EARLIEST_START PASS E6 capture/E7accept, E5 control rejected'
exit "$rc"
