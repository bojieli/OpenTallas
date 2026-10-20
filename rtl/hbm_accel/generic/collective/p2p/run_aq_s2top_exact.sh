#!/usr/bin/env bash
# L2H-GQ4 k4 (10-19): the production AQ13 configuration (OT_COLLQ_SRAM + OT_GQ_FAN32 + OT_GQ_S2TOP: stage-2 registered
# product top bit) against the closed references: tb_aq_tree13 (1,024 blocks vs ot_hdc_actquant) on ot_hgi_coll_aq13 and
# tb_aq_scale13r_eq (every a exponent field x random significands, both coefficients, vs ot_hbm_xp_aq_scale13).
# Usage: run_aq_s2top_exact.sh OUT [MUT]   MUT 0 = positive; 1 = OT_GQ_MUT_S2TOP_K (the 1/448 top-bit threshold for both
# coefficients) -> SCALE13R_EQ FAIL errors=... (must fail).
set -euo pipefail
OUT=$(realpath -m "$1"); MUT=${2:-0}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
P=rtl/hbm_accel/generic/collective/p2p
MEM=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
D=(-DOT_COLLQ_SRAM -DOT_GQ_FAN32 -DOT_GQ_S2TOP); [[ $MUT == 1 ]] && D+=(-DOT_GQ_MUT_S2TOP_K)
verilator --binary --timing -j 4 "${D[@]}" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_aq_scale13r_eq --Mdir "$OUT/sc" \
 "$P/tb_aq_scale13r_eq.sv" "$P/ot_hgi_coll_aq_scale13r.sv" physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv > "$OUT/sc.build.log" 2>&1 \
 || { tail -30 "$OUT/sc.build.log"; exit 2; }
"$OUT/sc/Vtb_aq_scale13r_eq" | tee "$OUT/sc.log" || true
grep -q '^SCALE13R_EQ PASS ' "$OUT/sc.log" || { echo "AQ_S2TOP SCALE13R_EQ not PASS"; exit 1; }
sed 's/ot_hbm_xp_aq_tree13 #(.MUT(MUT))/ot_hgi_coll_aq13 #(.LMUT(MUT))/' physical/hbm_xp_aq_tree13_1014/tb_aq_tree13.sv > "$OUT/tb.sv"
verilator --binary --timing -j 4 "${D[@]}" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb --Mdir "$OUT/aq" "$OUT/tb.sv" \
 "$P/ot_hgi_coll_aq13.sv" "$P/ot_hgi_coll_aq_scale13r.sv" rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv \
 rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_hc.sv rtl/hdc/ot_hdc_cg.sv "$MEM" > "$OUT/aq.build.log" 2>&1 \
 || { tail -30 "$OUT/aq.build.log"; exit 2; }
"$OUT/aq/Vtb" | tee "$OUT/aq.log" || true
grep -q '^AQ_TREE13_EXACT_PASS blocks1024 ' "$OUT/aq.log" || { echo "AQ_S2TOP AQ13 not PASS"; exit 1; }
echo "AQ_S2TOP_EXACT_PASS $(grep -m1 '^SCALE13R_EQ PASS' "$OUT/sc.log") | $(grep -m1 AQ_TREE13_EXACT_PASS "$OUT/aq.log")"
