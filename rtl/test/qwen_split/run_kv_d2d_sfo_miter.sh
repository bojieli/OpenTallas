#!/bin/bash
# KV-D2D 2026-10-19: lockstep miter qkd_d2d_static[_ovl] (as built) vs qkd_d2d_static[_ovl]_sf (safe fan-out) on the full
# 66-write cold sequence + lifecycle + random phases (rtl/test/qwen_split/tb_kv_d2d_sfo_miter.sv), Verilator.
# Usage: run_kv_d2d_sfo_miter.sh OUT    env: OVLM=1 (overlap masters), MUTFO=n (bench mutant), RANDINIT=1 SEED=n (every
# variable of both ends starts random: copy-convergence proof via OT_FO_CHECK), VERILATOR (default: verilator on PATH).
# Prints SFO_MITER_PASS and exits 0, or SFO_MITER_FAIL (mismatch / coverage / FO_COPY_MISMATCH) and exits 1.
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
 "$W/qwen_split/qfd_kvn_static_transport.sv"
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$W/test/qwen_split/tb_kv_d2d_sfo_miter.sv")
sha256sum "${SRC[@]}" > "$OUT/source.sha256"
"$V" --version > "$OUT/verilator.version" 2>&1
DEFS=(-DOT_FO_CHECK -DOT_MEM_NO_INIT "-DMUTFO_V=${MUTFO:-0}")
[ "${OVLM:-0}" = 1 ] && DEFS+=(-DOVLM)
[ "${RANDINIT:-0}" = 1 ] && DEFS+=(-DRANDINIT)
"$V" --binary --timing -j "${VJ:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-TIMESCALEMOD \
  "${DEFS[@]}" --top-module tb -Mdir "$OUT/obj" -o sim "${SRC[@]}" > "$OUT/build.log" 2>&1 \
  || { tail -30 "$OUT/build.log"; echo "SFO_MITER_FAIL build"; exit 2; }
PLUS=()
[ "${RANDINIT:-0}" = 1 ] && PLUS=(+verilator+rand+reset+2 "+verilator+seed+${SEED:-1}")
"$OUT/obj/sim" "${PLUS[@]}" > "$OUT/run.log" 2>&1
grep -E "SFO_MITER_|MISMATCH|FO_COPY_MISMATCH" "$OUT/run.log" | head -20
if grep -q FO_COPY_MISMATCH "$OUT/run.log"; then echo "SFO_MITER_FAIL FO_COPY_MISMATCH"; exit 1; fi
grep -q '^SFO_MITER_PASS' "$OUT/run.log" && ! grep -q 'SFO_MITER_FAIL' "$OUT/run.log" || { echo "SFO_MITER_FAIL"; exit 1; }
echo "SFO_MITER_PASS ovlm=${OVLM:-0} randinit=${RANDINIT:-0} seed=${SEED:-0} mutfo=${MUTFO:-0}"
