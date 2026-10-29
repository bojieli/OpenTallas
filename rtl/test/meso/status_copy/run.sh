#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory}
mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
V=(verilator --binary --timing --build -j 4 --top-module tb_status_copy -Wno-fatal)
SRC=("$R/rtl/test/meso/status_copy/tb_status_copy.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv")
"${V[@]}" --Mdir "$OUT/base" "${SRC[@]}" > "$OUT/build.log" 2>&1
for phase in 0 41 83 125 208 416 624 791; do "$OUT/base/Vtb_status_copy" +PHASE=$phase >> "$OUT/lockstep.log" 2>&1; done
"${V[@]}" -DOT_MESO_CA_MUTANT_STATUS_COPY --Mdir "$OUT/mut" "${SRC[@]}" > "$OUT/build_mut.log" 2>&1
if "$OUT/mut/Vtb_status_copy" +PHASE=125 > "$OUT/mutant.log" 2>&1; then echo 'STATUS_COPY_MUTANT_SURVIVED';exit 1;fi
grep -q STATUS_COPY_MISMATCH "$OUT/mutant.log"
echo 'STATUS_COPY_MUTANT_CAUGHT'
cat "$OUT/lockstep.log"
