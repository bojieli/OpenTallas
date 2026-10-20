#!/bin/bash
set -eu
ROOT=$(cd "${1:?root}" && pwd);OUT=${2:?out};CASE=${3:?case};mkdir -p "$OUT";OUT=$(cd "$OUT"&&pwd)
cd "$ROOT";V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
defs=();args=()
case "$CASE" in
 exact) ;;
 tput) args+=(+TPUT);;
 mutant_addr) defs+=(-DOT_MUT_MEMM);;
 mutant_bypass) defs+=(-DOT_CDC_IBMEM_MUT_NOBYPASS);;
 *) exit 2;;
esac
"$V" --version > "$OUT/version.txt"
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_safe -Mdir "$OUT/obj" -j 4 -o sim "${defs[@]}" $(cat rtl/test/host_cdc_safe_1020/sources.f) > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log";exit 2; }
"$OUT/obj/sim" "${args[@]}" > "$OUT/run.log" 2>&1
