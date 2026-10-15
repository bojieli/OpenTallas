#!/bin/bash
set -euo pipefail
SRC=$1
OUT=$2
mkdir -p "$OUT"
V=${OT_VERILATOR:-verilator}
for mode in exact mutant; do
  defs=()
  if [[ $mode == mutant ]]; then defs=(+define+OT_S81_MUT_INPUT_CREDITS); fi
  "$V" --binary --timing -j 8 -Wno-fatal "${defs[@]}" --top-module tb_s81_operand_credits --Mdir "$OUT/$mode" \
    "$SRC/rtl/lib/ot_reset_sync.sv" "$SRC/rtl/lib/ot_async_fifo.sv" \
    "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv" \
    "$SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_operand_credits.sv" > "$OUT/$mode.build.log" 2>&1
  "$OUT/$mode/Vtb_s81_operand_credits" > "$OUT/$mode.log" 2>&1
done
grep 'OPERAND_CREDITS PASS' "$OUT/exact.log"
grep 'OPERAND_CREDITS FAIL' "$OUT/mutant.log"
echo OPERAND_CREDITS_GATE_PASS
