#!/bin/bash
set -euo pipefail
R=$1;O=$2
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
S=$R/rtl/hbm_next/idxn
verilator --binary --timing -Wall -Wno-TIMESCALEMOD -Wno-PROCASSINIT -Wno-DECLFILENAME -Wno-PINCONNECTEMPTY -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-BLKSEQ --top-module tb_key_serial_chain -j 4 --Mdir "$O/obj" "$S/ot_hnx_idxn_key_serial_chain.sv" "$S/ot_hnx_idxn_keybuf_serial_np4.sv" "$S/ot_hnx_idxn_keybuf_slice.sv" "$S/ot_hnx_idxn_keybuf_sliced_np4.sv" "$R/rtl/test/hbm_key_serial_1029/tb_key_serial_chain.sv" "$R/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" > "$O/build.log" 2>&1
"$O/obj/Vtb_key_serial_chain" > "$O/nominal.log" 2>&1
for m in 2 3 4;do "$O/obj/Vtb_key_serial_chain" +MUT=$m > "$O/mutant$m.log" 2>&1;grep -q KEY_CHAIN_CONTROL_CAUGHT "$O/mutant$m.log";done
set +e
"$O/obj/Vtb_key_serial_chain" +MUT=1 > "$O/mutant1.log" 2>&1
rc=$?
set -e
test "$rc" != 0
grep -q KEY_CHAIN_PAYLOAD "$O/mutant1.log"
echo KEY_CHAIN_ALL_PASS
