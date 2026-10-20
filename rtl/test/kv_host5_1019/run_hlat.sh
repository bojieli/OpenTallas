#!/bin/bash
# KV-HOST5 10-19: H (HOST RESULT -> next kind-12 CONTEXT source) measurement bench.  Verilator 5.050 (daemon version).
# usage: run_hlat.sh ROOT OUT [TB]  TB = tb_kv_host5_hlat (default) | tb_kv_host5_hplane; every file a bench reads is in $TB.f
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
TB=${3:-tb_kv_host5_hlat}; L=$ROOT/rtl/test/kv_host5_1019/$TB.f
cd "$ROOT"
"$V" --version > "$OUT/verilator.txt"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module $TB -Mdir "$OUT/obj" -j ${VJ:-4} -o sim $(cat "$L") > "$OUT/build.log" 2>&1 \
  || { echo "HLAT BUILD-ERR"; grep -E '%Error' "$OUT/build.log" | head -20; exit 1; }
"$OUT/obj/sim" > "$OUT/$TB.log" 2>&1; rc=$?
rm -rf "$OUT/obj"
grep -E "^(PASS|FAIL)|H(LAT|PLANE)_SUMMARY" "$OUT/$TB.log"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$TB.log"
