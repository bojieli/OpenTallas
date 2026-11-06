#!/bin/bash
set -eu
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
R=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$(dirname "$0")"
for mode in pass mutant; do
 defs="+define+TB_WFALL +define+TB_FREG"
 [ "$mode" != mutant ] || defs="$defs +define+OT_MESO_CA_MUTANT_FREG"
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style $defs --top-module tb --Mdir "obj_$mode" -o tbx tb.sv "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv" > "build_$mode.log" 2>&1
 set +e
 "obj_$mode/tbx" +seed=173 +n=160 > "run_$mode.log" 2>&1
 rc=$?
 set -e
 echo "$mode rc $rc"
 tail -n 3 "run_$mode.log"
 if [ "$mode" = pass ]; then grep -q "errors=0 PASS$" "run_$mode.log"; else grep -q "WREG_EQUIV.* FAIL$" "run_$mode.log"; fi
done
