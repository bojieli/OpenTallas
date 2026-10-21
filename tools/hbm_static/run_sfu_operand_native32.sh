#!/bin/bash
set -euo pipefail
: "${OUT:?output directory required}"
mkdir -p "$OUT"
OUT=$(realpath "$OUT")
p=rtl/hbm_accel/generic/peers
m=physical/asap7_memory_macros
sources=(rtl/test/hbm_accel/generic/tb_hgi_sfu_static_operand_store.sv "$p/ot_hgi_sfu_static_operand_store.sv" "$p/ot_hgi_su_unit.sv" "$m/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$m/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" "$m/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v")
sha256sum "${sources[@]}" > "$OUT/bench_inputs.sha256"
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for cfg in default native;do
 args=()
 if [ "$cfg" = native ];then args=(-GNATIVE32=1 -GWROT=1 -GWPIPE=1);fi
 out="$OUT/bench_$cfg";mkdir -p "$out"
 "$v" --binary --timing -j 8 -O1 -Wno-fatal --top-module tb_hgi_sfu_static_operand_store "${args[@]}" --Mdir "$out/obj" "${sources[@]}" > "$out/build.log" 2>&1
 "$out/obj/Vtb_hgi_sfu_static_operand_store" > "$out/positive.log" 2>&1
 grep 'PASS SFU actual80SRAM' "$out/positive.log"
 if [ "$cfg" = native ];then
  for mut in MUT_ADDR MUT_RANGE MUT_SCALAR_ADDR;do
   set +e
   "$out/obj/Vtb_hgi_sfu_static_operand_store" +"$mut" > "$out/$mut.log" 2>&1
   rc=$?;set -e
   if [ "$rc" = 0 ];then echo "ESCAPED $mut";exit 1;fi
   grep -E 'STORE_WORD|STORE_FAULT|SCALAR_IDENTITY' "$out/$mut.log" > /dev/null
   echo "$mut REJECTED"
  done
 fi
done
