#!/bin/bash
set -euo pipefail
R=$(realpath "$1")
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for mode in positive mutant;do
  SRC=$R/s81_egress_min.sv
  [ "$mode" != mutant ] || SRC=$R/mutant.sv
  verilator --binary --timing -Wno-fatal --top-module tb_egress -j 8 --Mdir "$R/obj_$mode" "$R/cells.sv" "$SRC" "$R/tb_egress.sv" > "$R/build_$mode.log" 2>&1
  "$R/obj_$mode/Vtb_egress" > "$R/$mode.log" 2>&1
done
grep TRANSPORT_PASS "$R/positive.log"
grep TRANSPORT_FAIL "$R/mutant.log"
grep EGRESS "$R/positive.log" "$R/mutant.log"
