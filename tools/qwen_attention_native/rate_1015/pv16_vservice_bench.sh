#!/bin/bash
# pv16_vservice_bench.sh OUT [PAIR] [MUT] [VMUT] [MODE] [CTXS] [KINT=1]: build + run tb_qwen_pv16_vservice (8 x qkd_pv16_vport
# + ot_qwen_tp8_pv_wide_pair, rings popped at their head on compiled slots).  One PV16_VSERVICE line per context;
# exit 0 only if every line is PASS (negative controls expect FAIL).  Fails closed on a golden-generator error.
set -u
O=$1;P=${2:-0};M=${3:-0};VM=${4:-0};MODE=${5:-steady};CTXS=${6:-"1 100 129 300 1000 2049 4097 8192"};KI=${7:-1}
mkdir -p "$O";VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 16 \
 --hierarchical --top-module tb_qwen_pv16_vservice -GPAIR=$P -GMUT=$M -GVMUT=$VM -GKINT=$KI --Mdir "$O/obj_p${P}m${M}v${VM}k${KI}" \
 tools/qwen_attention_native/rate_1015/pv_pair_bench.vlt rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fpu.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 rtl/qwen_sys/static_kv_20261014/qkd_pv16_vport.sv rtl/test/nearhbm/tb_qwen_pv16_vservice.sv \
 > "$O/build_p${P}m${M}v${VM}k${KI}.log" 2>&1 || { echo "PV16_VSERVICE FAIL build"; tail -5 "$O/build_p${P}m${M}v${VM}k${KI}.log"; exit 1; }
rc=0
for T in $CTXS; do
 rm -rf "$O/vec_${T}_p$P"
 python3 tools/qwen_attention_native/rate_1015/pv_pair_ref.py --ctx $T --pair $P --seed $T --out "$O/vec_${T}_p$P" >/dev/null \
  || { echo "PV16_VSERVICE FAIL T=$T golden reference generation failed"; rc=1; continue; }
 line=$("$O/obj_p${P}m${M}v${VM}k${KI}/Vtb_qwen_pv16_vservice" +VEC="$O/vec_${T}_p$P" +CTX=$T +MODE=$MODE | grep -E "^PV16_VSERVICE|MISMATCH|RING_" | tail -1)
 echo "$line"; case "$line" in "PV16_VSERVICE PASS"*) ;; *) rc=1;; esac
done
exit $rc
