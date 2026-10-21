#!/bin/bash
# KV-PVW 10-19: composition bench of the GEN9-bound PV pair frame qkd_pvw_die_tb (qkd_pvw_die_t_f_ba.sv; OT_KV_BOOT_AGES=1,
# OT_KV_RS_HD auto -> f) = tb_qkd_pvw_die_tb (Verilator 5.050) against the old pair's golden at each context.
# pv_trunk_ba_bench.sh OUT [TRUNK_MUT] [FLAG_D_ADJ] [CTXS]   (from the repository root or an export of it)
# env RL (default 19) = boundary round trip; boot word cfg_age byte PAIR = RL+1+AGE_ADJ (env AGE_ADJ, -1 = negative control);
# env CFG_SWAP=1 = negative control (right age only in the other pair's byte).  env PAIR (default 0).
# One PV_PAIR_TB PASS|FAIL line per context; exit 0 only if every line is PASS (negative controls expect FAIL).
set -u
O=$1;TM=${2:-0};FA=${3:-0};RL=${RL:-19};AA=${AGE_ADJ:-0};CS=${CFG_SWAP:-0};PR=${PAIR:-0};CTXS=${4:-"1 100 300 1000 4097 8192"}
mkdir -p "$O";VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
B="obj_m${TM}_f${FA}_rl${RL}_a${AA}_s${CS}_p${PR}"
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs ${JOBS:-16} \
 --hierarchical --top-module tb_qkd_pvw_die_tb -GTRUNK_MUT=$TM -GFLAG_D_ADJ=$FA -GRL=$RL -GAGE_ADJ=$AA -GCFG_SWAP=$CS -GPAIR=$PR \
 --Mdir "$O/$B" -Irtl/test/nearhbm \
 tools/qwen_attention_native/rate_1015/pv_pair_bench.vlt rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tb.sv \
 rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fpu.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv rtl/qwen_sys/split_20261014/qkd_pv_rtrunk.sv \
 rtl/qwen_sys/split_20261014/qkd_pvw_die_t_f_ba.sv rtl/test/nearhbm/tb_qkd_pvw_die_tb.sv \
 > "$O/build_$B.log" 2>&1 || { echo "PV_PAIR_TB FAIL build"; tail -5 "$O/build_$B.log"; exit 1; }
rc=0
for T in $CTXS; do
 V="$O/vec_${PR}_${T}"
 [ -f "$V/gold.hex" ] || python3 tools/qwen_attention_native/rate_1015/pv_pair_ref.py --ctx $T --pair $PR --seed $T --out "$V" >/dev/null \
  || { echo "PV_PAIR_TB FAIL T=$T golden reference generation failed"; rc=1; continue; }
 line=$("$O/$B/Vtb_qkd_pvw_die_tb" +VEC="$V" +CTX=$T | grep -E "^PV_PAIR_TB|MISMATCH|AGE" | tail -1)
 echo "$line"; case "$line" in "PV_PAIR_TB PASS"*) ;; *) rc=1;; esac
done
exit $rc
