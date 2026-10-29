#!/bin/bash
# Use through ot-run with an own staged checkout/runtime. No physical qualification.
set -euo pipefail
R=$1;O=$2
mkdir -p "$O"
S=$R/rtl/hbm_next/idxn
verilator --binary --timing -j "${JOBS:-1}" -Wno-fatal --top-module tb_key_epoch --Mdir "$O/obj" \
 "$S/ot_hnx_idxn_key_prefill_control.sv" "$S/ot_hnx_idxn_key_serial_chain.sv" \
 "$S/ot_hnx_idxn_keybuf_serial_np4.sv" "$S/ot_hnx_idxn_keybuf_slice.sv" \
 "$R/rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv" "$R/rtl/test/hbm_key_epoch_1029/tb_key_epoch.sv" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" > "$O/build.log" 2>&1
"$O/obj/Vtb_key_epoch" > "$O/nominal.log" 2>&1
for m in 1 2 3;do "$O/obj/Vtb_key_epoch" +MUT=$m > "$O/mutant$m.log" 2>&1;grep -q KEY_EPOCH_CONTROL_CAUGHT "$O/mutant$m.log";done
cat "$O/nominal.log"
echo KEY_EPOCH_ALL_PASS
