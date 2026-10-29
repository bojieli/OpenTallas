#!/bin/bash
set -euo pipefail
SRC=$1
OUT=$2
mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
python3 "$SRC/results/codex_kv_kits_1028/ahub/clock_miter.py" "$SRC/results/codex_kv_kits_1028/ahub/ck3/qkd_ahub_static_dw.sv" "$OUT/tb.sv"
iverilog -g2012 -s tb -o "$OUT/tb0" "$OUT/tb.sv"
vvp "$OUT/tb0" | tee "$OUT/nominal.log"
iverilog -g2012 -s tb -Ptb.MUT=1 -o "$OUT/tb1" "$OUT/tb.sv"
if vvp "$OUT/tb1" > "$OUT/mutant.log" 2>&1; then
  echo 'CLOCK_MITER FAIL mutant escaped'; exit 1
fi
grep 'CLOCK_MITER mismatch3' "$OUT/mutant.log"
echo 'CLOCK_MITER MUTANT CAUGHT'
