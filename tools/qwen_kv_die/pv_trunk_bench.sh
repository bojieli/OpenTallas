#!/bin/bash
# KVPLAN 1815: build + run tb_qkd_pvw_die_t (Verilator) on the generated trunked PV pair at each context.
# pv_trunk_bench.sh OUT [TRUNK_MUT] [FLAG_D_ADJ] [CTXS]  (run from the repository root or an export of it)
# One PV_PAIR_T PASS|FAIL line per context; exit 0 only if every line is PASS (negative controls expect FAIL).
set -u
O=$1;TM=${2:-0};FA=${3:-0};CTXS=${4:-"1 100 300 1000 4097 8192"}
mkdir -p "$O";VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 16 \
 --hierarchical --top-module tb_qkd_pvw_die_t -GTRUNK_MUT=$TM -GFLAG_D_ADJ=$FA --Mdir "$O/obj_m${TM}_f${FA}" -Irtl/test/nearhbm \
 tools/qwen_attention_native/rate_1015/pv_pair_bench.vlt rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_t.sv \
 rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fpu.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv \
 rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv rtl/test/nearhbm/tb_qkd_pvw_die_t.sv \
 > "$O/build_m${TM}_f${FA}.log" 2>&1 || { echo "PV_PAIR_T FAIL build"; tail -5 "$O/build_m${TM}_f${FA}.log"; exit 1; }
rc=0
for T in $CTXS; do
 V="$O/vec_${T}"
 [ -f "$V/gold.hex" ] || python3 tools/qwen_attention_native/rate_1015/pv_pair_ref.py --ctx $T --pair 0 --seed $T --out "$V" >/dev/null \
  || { echo "PV_PAIR_T FAIL T=$T golden reference generation failed"; rc=1; continue; }
 line=$("$O/obj_m${TM}_f${FA}/Vtb_qkd_pvw_die_t" +VEC="$V" +CTX=$T | grep -E "^PV_PAIR_T|MISMATCH|AGE" | tail -1)
 echo "$line"; case "$line" in "PV_PAIR_T PASS"*) ;; *) rc=1;; esac
done
exit $rc
