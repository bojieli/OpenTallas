#!/bin/bash
# KV-SRAM-D2D 2026-10-19: first-epoch guard bench (rtl/test/qwen_split/tb_kv_d2d_sfm_guard.sv), Verilator.
# Usage: run_kv_d2d_sfm_guard.sh OUT    env: OVLM=1 (overlap master), MUTFO=5 (TX guard disabled: must FAIL), VERILATOR.
set -u
OUT=$1
W=$(cd "$(dirname "$0")/../.." && pwd); R=$(cd "$W/.." && pwd)
V=${VERILATOR:-verilator}
mkdir -p "$OUT"
SRC=("$W/lib/ot_rst_pipe.sv" "$W/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv" "$W/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv"
 "$W/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$W/qwen_sys/split_20261014/qkd_native_attention_record.sv"
 "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_services.sv"
 "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_ovl.sv"
 "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_safe_fo.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_sfo.sv"
 "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv" "$W/qwen_split/qfd_kvn_static_transport.sv"
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$R/physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p192/d2d_sram_1r1w_64x137_m1_r2c2_p192.v"
 "$R/physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p288/d2d_sram_1r1w_64x137_m1_r2c2_p288.v"
 "$W/test/qwen_split/tb_kv_d2d_sfm_guard.sv")
sha256sum "${SRC[@]}" > "$OUT/source.sha256"
"$V" --version > "$OUT/verilator.version" 2>&1
DEFS=(-DOT_MEM_NO_INIT "-DMUTFO_V=${MUTFO:-0}")
[ "${OVLM:-0}" = 1 ] && DEFS+=(-DOVLM)
"$V" --binary --timing -j "${VJ:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-TIMESCALEMOD \
  "${DEFS[@]}" --top-module tb -Mdir "$OUT/obj" -o sim "${SRC[@]}" > "$OUT/build.log" 2>&1 \
  || { tail -30 "$OUT/build.log"; echo "GUARD_FAIL build"; exit 2; }
"$OUT/obj/sim" > "$OUT/run.log" 2>&1
grep -E "GUARD" "$OUT/run.log" | head -10
grep -q '^GUARD_PASS' "$OUT/run.log" || { echo "GUARD_FAIL"; exit 1; }
