#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}
mkdir -p "$out"
sources=(rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_bank_shell_static.sv rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_bank_memory_static.sv rtl/test/tb_hgi_hc_bank_shell_memory_static.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
for mut in 0 1;do
  iverilog -g2012 -s tb_hgi_hc_bank_shell_memory_static -Ptb_hgi_hc_bank_shell_memory_static.MUT=$mut -o "$out/m$mut.vvp" "${sources[@]}" > "$out/m$mut.compile.log" 2>&1
  set +e
  vvp "$out/m$mut.vvp" > "$out/m$mut.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]];then [[ $rc == 0 ]];grep 'BANK_SHELL_MEMORY PASS' "$out/m$mut.log";else [[ $rc != 0 ]];grep 'BANK_SHELL_MEMORY mismatch' "$out/m$mut.log";fi
done
