#!/bin/bash
# Full N4/8-owner chain, target EP RTL and mapped SRAM; external ri stimuli only.
set -eu
R=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$1; MUT=${2:-0}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
S=$R/rtl/qwen_sys/split_20261014
M=$R/physical/qkd_astk_strip/macros
"$V" --binary -j 4 --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_qkd_astk_er_chain_st -DKVD_ERMUT="$MUT" -DKVD_ER_RL="${KVD_ER_RL:-3}" \
 -Mdir "$OUT/obj" -o Vtb \
 "$R/rtl/test/qwen_kv_die/tb_qkd_astk_er_chain_st.sv" "$S/qkd_astk_er_owner_st.sv" "$S/qkd_astk_er_chain_st.sv" "$S/qkd_astk_phys.sv" "$S/qkd_astk_static_leaves.sv" \
 "$R/rtl/hdc/ot_hdc_delay.sv" "$R/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$R/rtl/hdc/ot_hdc_fp32_add_lat_nr.sv" \
 "$R/rtl/hdc/ot_hdc_fp32_mul_lat.sv" "$R/rtl/hdc/ot_hdc_sfu.sv" "$R/rtl/hdc/ot_hdc_prefix.sv" "$R/rtl/hdc/ot_hdc_fastfp.sv" \
 "$M/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v" \
 "$M/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v" >"$OUT/build.log" 2>&1 || { tail -25 "$OUT/build.log"; exit 1; }
"$OUT/obj/Vtb" >"$OUT/run.log" 2>&1
grep -E '^(PASS|FAIL|INFO)' "$OUT/run.log" | head -12
grep -q '^PASS qkd_astk_er_chain_st' "$OUT/run.log"
