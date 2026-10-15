#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1");shift;mkdir -p "$OUT";cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
"$V" --binary --timing -O2 -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_hgi_coll_static_program_target --Mdir "$OUT/obj" "$@" \
 "$P/tb_hgi_coll_static_program_target.sv" "$P/ot_hgi_coll_static_program_target.sv" "$P/ot_hgi_coll_static_issuer.sv" physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log";exit 2; }
"$OUT/obj/Vtb_hgi_coll_static_program_target" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^PROGRAM_JOIN PASS ' "$OUT/run.log"
for scenario in $(seq 1 20);do
 "$OUT/obj/Vtb_hgi_coll_static_program_target" +fault="$scenario" > "$OUT/fault-$scenario.log" 2>&1
 grep -q '^PROGRAM_JOIN FAULT PASS ' "$OUT/fault-$scenario.log"
 cat "$OUT/fault-$scenario.log"
done
