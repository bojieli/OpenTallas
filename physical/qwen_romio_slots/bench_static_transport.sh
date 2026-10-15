#!/usr/bin/env bash
set -euo pipefail
OUT=$1; MUT=${2:-0}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
iverilog -g2012 -s tb_qfd_static_transport -Ptb_qfd_static_transport.MUT="$MUT" -o "$OUT/sim" \
 "$R/rtl/test/tb_qfd_static_transport.sv" "$R/rtl/physical/ot_qfd_static_transport.sv" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" > "$OUT/build.log" 2>&1
vvp -n "$OUT/sim" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^PASS static_transport' "$OUT/run.log"
