#!/bin/bash
# pv_pair_bench.sh OUT [PAIR] [MUT] [MODE] [CTXS]: build + run tb_qwen_tp8_pv_wide_pair_mc (Verilator) at each context.
# Prints one PV_PAIR PASS|FAIL line per context; exit 0 only if every line is PASS (negative controls expect FAIL).
set -u
O=$1;P=${2:-0};M=${3:-0};MODE=${4:-steady};CTXS=${5:-"1 100 129 300 1000 2049 4097 8192"}
mkdir -p "$O";VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 16 \
 --hierarchical --top-module tb_qwen_tp8_pv_wide_pair_mc -GPAIR=$P -GMUT=$M -GCTL_RESET_PIN=${CTL_RESET_PIN:-0} -GLEAF_RESET_PIN=${LEAF_RESET_PIN:-0} --Mdir "$O/obj_p${P}m${M}" \
 tools/qwen_attention_native/rate_1015/pv_pair_bench.vlt rtl/hdc/nearhbm/qkd_pv_wide_pair_mc.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fpu.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/test/nearhbm/tb_qwen_tp8_pv_wide_pair_mc.sv \
 > "$O/build_p${P}m${M}.log" 2>&1 || { echo "PV_PAIR FAIL build"; exit 1; }
rc=0
for T in $CTXS; do
 rm -rf "$O/vec_${T}_p$P"
 python3 tools/qwen_attention_native/rate_1015/pv_pair_ref.py --ctx $T --pair $P --seed $T --out "$O/vec_${T}_p$P" >/dev/null \
  || { echo "PV_PAIR FAIL T=$T golden reference generation failed"; rc=1; continue; }
 line=$("$O/obj_p${P}m${M}/Vtb_qwen_tp8_pv_wide_pair_mc" +VEC="$O/vec_${T}_p$P" +CTX=$T +MODE=$MODE | grep -E "^PV_PAIR|MISMATCH" | tail -1)
 echo "$line"; case "$line" in "PV_PAIR PASS"*) ;; *) rc=1;; esac
done
exit $rc
