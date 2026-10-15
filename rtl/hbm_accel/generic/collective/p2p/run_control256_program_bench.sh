#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=${1:?output directory};shift
mkdir -p "$OUT"
p=$ROOT/rtl/hbm_accel/generic/collective/p2p
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing -O2 -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_hgi_coll_control256_program --Mdir "$OUT/obj" "$@" \
 "$p/tb_hgi_coll_control256_program.sv" "$p/ot_hgi_coll_control256_program.sv" "$p/ot_hgi_coll_static_issuer.sv" \
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log";exit 2; }
"$OUT/obj/Vtb_hgi_coll_control256_program" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^CONTROL256_PROGRAM PASS ' "$OUT/run.log"
for scenario in $(seq 1 17);do
 "$OUT/obj/Vtb_hgi_coll_control256_program" +fault="$scenario" > "$OUT/fault-$scenario.log" 2>&1
 grep -q '^CONTROL256_PROGRAM FAULT PASS ' "$OUT/fault-$scenario.log"
done
