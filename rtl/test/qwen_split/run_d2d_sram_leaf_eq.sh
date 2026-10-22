#!/bin/bash
# KV-SRAM-D2D 2026-10-19: slot-store bank equivalence (as-built 64x512 leaf vs right-sized d2d_sram 64x137 leaf) +
# lifetime scoreboard (rtl/test/qwen_split/tb_d2d_sram_leaf_eq.sv), Verilator.  Usage: run_d2d_sram_leaf_eq.sh OUT
# env: SRAMV=1|2, MUTW=1 (column-136 write mutant), INIT=0 (OT_MEM_NO_INIT: both macros power up X), VERILATOR.
set -u
OUT=$1
W=$(cd "$(dirname "$0")/../.." && pwd); R=$(cd "$W/.." && pwd)
V=${VERILATOR:-verilator}
mkdir -p "$OUT"
SRC=("$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_safe_fo.sv" "$W/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv"
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$R/physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p192/d2d_sram_1r1w_64x137_m1_r2c2_p192.v"
 "$R/physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p288/d2d_sram_1r1w_64x137_m1_r2c2_p288.v"
 "$W/test/qwen_split/tb_d2d_sram_leaf_eq.sv")
sha256sum "${SRC[@]}" > "$OUT/source.sha256"
"$V" --version > "$OUT/verilator.version" 2>&1
DEFS=("-DSRAMV_V=${SRAMV:-1}" "-DMUTW_V=${MUTW:-0}")
[ "${INIT:-1}" = 0 ] && DEFS+=(-DOT_MEM_NO_INIT)
"$V" --binary --timing -j "${VJ:-4}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-TIMESCALEMOD \
  "${DEFS[@]}" --top-module tb -Mdir "$OUT/obj" -o sim "${SRC[@]}" > "$OUT/build.log" 2>&1 \
  || { tail -30 "$OUT/build.log"; echo "LEAF_EQ_FAIL build"; exit 2; }
"$OUT/obj/sim" > "$OUT/run.log" 2>&1
grep -E "LEAF_EQ_|MISMATCH" "$OUT/run.log" | head -8
grep -q '^LEAF_EQ_PASS' "$OUT/run.log" || { echo "LEAF_EQ_FAIL"; exit 1; }
