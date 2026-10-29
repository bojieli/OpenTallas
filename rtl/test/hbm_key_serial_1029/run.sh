#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd)
O=$(mkdir -p "${1:?output}" && readlink -f "$1")
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
S=$R/rtl/hbm_next/idxn
verilator --binary --timing -Wall -Wno-TIMESCALEMOD -Wno-PROCASSINIT -Wno-DECLFILENAME -Wno-PINCONNECTEMPTY -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-BLKSEQ --top-module tb_key_serial -j 4 --Mdir "$O/obj" "$S/ot_hnx_idxn_keybuf_slice.sv" "$S/ot_hnx_idxn_keybuf_sliced_np4.sv" "$S/ot_hnx_idxn_keybuf_serial_np4.sv" "$R/rtl/test/hbm_key_serial_1029/tb_key_serial.sv" "$R/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" > "$O/build.log" 2>&1
"$O/obj/Vtb_key_serial" > "$O/nominal.log" 2>&1
for m in 1 2 3 4;do "$O/obj/Vtb_key_serial" +MUT=$m > "$O/mutant$m.log" 2>&1;grep -q SERIAL_MUTANT_CAUGHT "$O/mutant$m.log";done
set +e
"$O/obj/Vtb_key_serial" +MUT=5 > "$O/mutant5.log" 2>&1
rc=$?
set -e
test "$rc" != 0
grep -q SERIAL_DATA_MUTANT_CHECK "$O/mutant5.log"
echo KEY_SERIAL_ALL_PASS
