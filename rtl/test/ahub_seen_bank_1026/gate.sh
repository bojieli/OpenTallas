#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
P=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$P/out}
mkdir -p "$OUT"
for m in 0 1;do
 verilator --binary -j 4 --timing -Wno-fatal -Wno-MULTIDRIVEN --top-module tb -GMUT=$m -Mdir "$OUT/obj$m" -o Vtb "$P/ref.sv" "$P/dut.sv" "$P/tb.sv" > "$OUT/build$m.log" 2>&1
 "$OUT/obj$m/Vtb" > "$OUT/run$m.log" 2>&1
 cat "$OUT/run$m.log"
done
