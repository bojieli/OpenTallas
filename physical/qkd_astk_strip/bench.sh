#!/usr/bin/env bash
# Aggregator strip masters (el1013-qwen-kvstrips): exact bench against the golden aggregator (stack_h minus engines).
#   bench.sh OUT_DIR [MUT [RL [STACKS]]]   MUT 0 | 1 pv | 2 ep | 3 zn | 4 ctl | 5 ex; RL relay stations a die net (1);
#                                         STACKS "0 1 2 3" (mutant runs: stack 0, the T = 8192 layer only)
#   env ASTK_DEFS: extra +define+ profile (native TP8: "+define+KVD_HEADS=1 +define+KVD_Q_FP32=1")
# Prints "PASS qkd_astk all <n> stacks exact" (rc 0) or "FAIL qkd_astk mutant <m> detected ..." (rc 1).
set -u
OUT=$1; MUT=${2:-0}; RL=${3:-1}; STACKS=${4:-"0 1 2 3"}; [ "$MUT" != 0 ] && STACKS=${4:-0}
[ "$MUT" != 0 ] && TARG=${TARG:-8192}        # a mutant: one full layer of stack 0
R=$(cd "$(dirname "$0")/../.." && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
W=$R/rtl
python3 "$R/tools/qwen_kv_die/astk_gold_gen.py" "$OUT/ot_qkd_astk_gold.sv" || { echo "FAIL qkd_astk gold gen"; exit 1; }
awk '/^module ot_hdc_lzc32/,/^endmodule/' $W/hdc/ot_hdc_fastfp.sv > "$OUT/lzc.sv"
awk '/^module ot_hdc_fp32_add_lat_nr /{s=1} !s{print} s&&/^endmodule/{s=0}' $W/hdc/ot_hdc_fp32_add_lat_nr.sv > "$OUT/nr_rest.sv"
# ASTK_SEG=1 (Q-KVSYS-STRIP 2026-10-16): the dut is the SEGMENTED strip ot_qkd_astk_strip_seg (4 x qkd_astk_seg +
# the unchanged hub end, rtl/qwen_sys/split_20261014/qkd_astk_seg.sv) instead of the benched die wiring ot_qkd_astk_strip
TB=$W/test/qwen_kv_die/tb_qkd_astk.sv
if [ "${ASTK_SEG:-0}" = 1 ]; then
  sed 's/ot_qkd_astk_strip #(/ot_qkd_astk_strip_seg #(/' "$TB" > "$OUT/tb_qkd_astk_seg.sv"; TB="$OUT/tb_qkd_astk_seg.sv $W/qwen_sys/split_20261014/qkd_astk_seg.sv"
fi
SRC="$TB $OUT/ot_qkd_astk_gold.sv $W/test/qwen_kv_die/ot_qwen_nearhbm_attn_stack_k.sv $W/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv
 $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $W/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv $W/hdc/nearhbm/ot_qkh_subtiles.sv $W/lib/ot_rst_relay.sv
 $OUT/nr_rest.sv $W/test/nearhbm/sim_nhb_fp_lat_nr_dpi.sv $W/test/nearhbm/sim_nhb_fp_lat_dpi.sv $W/hdc/ot_hdc_delay.sv $W/hdc/ot_hdc_sfu.sv
 $W/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv $W/hdc/ot_hdc_prefix.sv $OUT/lzc.sv $W/hdc/nearhbm/ot_qwen_nearhbm_prod.sv $W/hdc/ot_hdc_sfu_q.sv
 $W/hdc/ot_hdc_fpu.sv $W/hdc/ot_hdc_fp32_mul_pipe.sv $W/proto/ot_fp32_add_rne_pipe.sv $W/test/sim_hdc_v41x_fastfp_dpi.sv $W/test/sim_hdc_v41x_fastfp_wrap.sv
 $R/physical/qkd_astk_strip/macros/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v
 $R/physical/qkd_astk_strip/macros/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v
 $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
CPP="$W/test/nearhbm/sim_nhb_fp_lat_dpi.cpp $W/test/sim_hdc_v41x_fastfp_dpi.cpp"
: > "$OUT/all.log"
for s in $STACKS; do
  ( $V --binary --timing -O2 -j ${JOBS:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD -Wno-MODDUP \
      --x-assign fast --x-initial fast +define+KVD_LFB=4 +define+KVD_ND=1 +define+KVD_AKMUT=$MUT +define+KVD_AKRL=$RL ${ASTK_DEFS:-} \
      --top-module tb_qkd_astk -GS=$s --Mdir "$OUT/obj_s$s" -CFLAGS "-O1" $SRC $CPP > "$OUT/build_s$s.log" 2>&1 \
      || { grep -m 12 -E '%Error' "$OUT/build_s$s.log" | cut -c1-300; tail -3 "$OUT/build_s$s.log" | cut -c1-300; echo "FAIL qkd_astk build S=$s"; exit 0; }
    "$OUT/obj_s$s/Vtb_qkd_astk" ${TARG:+ +T=$TARG} > "$OUT/run_s$s.log" 2>&1
    grep -E '^(MISMATCH|LAYER|PASS|FAIL)' "$OUT/run_s$s.log" | head -40 ) > "$OUT/s$s.log" 2>&1 &
done
wait
cat "$OUT"/s*.log > "$OUT/all.log"; grep -E '^(LAYER|PASS|FAIL)' "$OUT/all.log"; grep '^MISMATCH' "$OUT/all.log" | head -12
n=$(grep -c '^PASS qkd_astk' "$OUT/all.log"); f=$(grep -c '^FAIL' "$OUT/all.log"); want=$(echo $STACKS | wc -w)
if [ "$n" = "$want" ] && [ "$f" = 0 ]; then echo "PASS qkd_astk all $n stacks exact (RL $RL)"; exit 0; fi
echo "FAIL qkd_astk mutant $MUT detected: $n of $want stacks pass"; exit 1
