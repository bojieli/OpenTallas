#!/bin/bash
# KV-HOST5 10-19: H (HOST RESULT -> next kind-12 CONTEXT source) measurement bench.  Verilator 5.050 (daemon version).
# usage: run_hlat.sh ROOT OUT   (every file the bench reads is in tb_kv_host5_hlat.f)
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$ROOT/rtl/test/kv_host5_1019/tb_kv_host5_hlat.f
cd "$ROOT"
"$V" --version > "$OUT/verilator.txt"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module tb_kv_host5_hlat -Mdir "$OUT/obj" -j ${VJ:-4} -o sim $(cat "$L") > "$OUT/build.log" 2>&1 \
  || { echo "HLAT BUILD-ERR"; grep -E '%Error' "$OUT/build.log" | head -20; exit 1; }
"$OUT/obj/sim" > "$OUT/tb_kv_host5_hlat.log" 2>&1; rc=$?
rm -rf "$OUT/obj"
grep -E '^(PASS|FAIL)|HLAT_SUMMARY' "$OUT/tb_kv_host5_hlat.log"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/tb_kv_host5_hlat.log"
