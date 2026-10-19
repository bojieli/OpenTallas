#!/bin/bash
# KV-RTRUNK 10-17: build + run tb_qkd_pvw_die_t_rs (Verilator): the generated trunked PV pair's result stream rs_* in
# lockstep with its 16,384-b po, at each context.  pv_rtrunk_bench.sh OUT [RS_MUT] [CTXS]  (from the repository root)
# env RL (default 19) = boundary round trip, ctl FIRST_INPUT_AGE = RL+1+AGE_ADJ (env AGE_ADJ, default 0; -1 = negative control).
# env PVW (default rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv) = the generated pair netlist to bench (AD3-KV-RSHD 10-18).
# One PV_PAIR_RS PASS|FAIL line per context; exit 0 only if every line is PASS (negative controls expect FAIL).
set -u
O=$1;RM=${2:-0};TM=0;FA=0;RL=${RL:-19};AA=${AGE_ADJ:-0};CTXS=${3:-"1 100 1000 8192"}
mkdir -p "$O";VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs ${JOBS:-16} \
 --hierarchical --top-module tb_qkd_pvw_die_t_rs -GRS_MUT=$RM -GRL=$RL -GAGE_ADJ=$AA --Mdir "$O/obj_rs${RM}" -Irtl/test/nearhbm \
 tools/qwen_attention_native/rate_1015/pv_pair_bench.vlt rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_t.sv \
 rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fpu.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv \
 rtl/qwen_sys/split_20261014/qkd_pv_rtrunk.sv ${PVW:-rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv} rtl/test/nearhbm/tb_qkd_pvw_die_t_rs.sv \
 > "$O/build_rs${RM}.log" 2>&1 || { echo "PV_PAIR_RS FAIL build"; tail -5 "$O/build_rs${RM}.log"; exit 1; }
rc=0
for T in $CTXS; do
 V="$O/vec_${T}"
 [ -f "$V/gold.hex" ] || python3 tools/qwen_attention_native/rate_1015/pv_pair_ref.py --ctx $T --pair 0 --seed $T --out "$V" >/dev/null \
  || { echo "PV_PAIR_RS FAIL T=$T golden reference generation failed"; rc=1; continue; }
 line=$("$O/obj_rs${RM}/Vtb_qkd_pvw_die_t_rs" +VEC="$V" +CTX=$T | grep -E "^PV_PAIR_RS" | tail -1)
 echo "$line"; case "$line" in "PV_PAIR_RS PASS"*) ;; *) rc=1;; esac
done
exit $rc
