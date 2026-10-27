#!/bin/bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
OUT=${1:?scratch output}
mkdir -p "$OUT"
SRC=("$ROOT/results/hbm_keybuf_slice_1027/ref_sram_256x256.v" "$HERE/gold_native_keybuf.sv" "$ROOT/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_slice.sv" "$ROOT/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_quarter.sv" "$HERE/tb_quarter.sv")
for half in 0 1; do
  iverilog -g2012 -s tb -Ptb.HALF=$half -o "$OUT/half${half}.vvp" "${SRC[@]}"
  vvp "$OUT/half${half}.vvp" > "$OUT/half${half}.log"
  tail -2 "$OUT/half${half}.log"
done
iverilog -g2012 -s tb -Ptb.HALF=1 -Ptb.MUT=1 -o "$OUT/mutant.vvp" "${SRC[@]}"
if vvp "$OUT/mutant.vvp" > "$OUT/mutant.log"; then echo MUTANT_ESCAPED;exit 1;else echo MUTANT_CAUGHT;fi
