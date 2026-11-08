#!/bin/bash
set -euo pipefail
cd /
S=$(dirname "$(readlink -f "$0")")
mkdir -p "$S/out"
touch "$S/.keep" "$S/out/.keep"
for m in 0 26 27; do
  iverilog -g2012 -s tb_fifo_local3 -Ptb_fifo_local3.MUT=$m -o "$S/out/m$m.vvp" "$S/tb_fifo_local3.sv" "$S/fifo_gold.sv" "$S/fifo_local3.sv" "$S/ot_reset_sync.sv"
  for pair in 3:5 5:3 3:13; do
    w=${pair%:*};r=${pair#*:}
    vvp "$S/out/m$m.vvp" +WH=$w +RH=$r > "$S/out/m${m}_${w}_${r}.log"
    if [ "$m" = 0 ]; then grep '^PASS' "$S/out/m${m}_${w}_${r}.log"; else grep '^FAIL' "$S/out/m${m}_${w}_${r}.log"; fi
  done
done
