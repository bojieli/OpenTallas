#!/bin/bash
set -euo pipefail
root=$(pwd)
cd "$root/src"
mkdir -p "$root/out"
p=rtl/hbm_accel/generic/peers
m=physical/asap7_memory_macros
sources=(rtl/test/hbm_accel/generic/tb_hgi_sfu_static_operand_store.sv "$p/ot_hgi_sfu_static_operand_store.sv" "$p/ot_hgi_su_unit.sv" "$p/ot_hgi_sfu_fault_tree.sv" "$m/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$m/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" "$m/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v")
sha256sum "${sources[@]}" > "$root/out/sources.sha256"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 8 -O1 -Wno-fatal --top-module tb_hgi_sfu_static_operand_store -GNATIVE32=1 -GWROT=1 -GWPIPE=1 --Mdir "$root/out/obj" "${sources[@]}" > "$root/out/build.log" 2>&1
"$root/out/obj/Vtb_hgi_sfu_static_operand_store" > "$root/out/positive.log" 2>&1
grep 'PASS SFU actual80SRAM' "$root/out/positive.log"
for mut in MUT_ADDR MUT_RANGE MUT_SCALAR_ADDR;do
 set +e
 "$root/out/obj/Vtb_hgi_sfu_static_operand_store" +"$mut" > "$root/out/$mut.log" 2>&1
 rc=$?
 set -e
 test "$rc" != 0
 grep -E 'STORE_WORD|STORE_FAULT|SCALAR_IDENTITY' "$root/out/$mut.log" > /dev/null
 echo "$mut REJECTED"
done
