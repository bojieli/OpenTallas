#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
OUT=$1
mkdir -p "$OUT"
for PREV_MODE in 0 1; do
  iverilog -g2012 -s tb -Ptb.PREV="$PREV_MODE" -o "$OUT/exact_$PREV_MODE" "$HERE/fifo_hlat_probe.sv"
  vvp "$OUT/exact_$PREV_MODE" | tee "$OUT/exact_$PREV_MODE.log"
  iverilog -g2012 -s tb -Ptb.PREV="$PREV_MODE" -DFQ_STALE_MUT -o "$OUT/mutant_$PREV_MODE" "$HERE/fifo_hlat_probe.sv"
  vvp "$OUT/mutant_$PREV_MODE" | tee "$OUT/mutant_$PREV_MODE.log"
done
