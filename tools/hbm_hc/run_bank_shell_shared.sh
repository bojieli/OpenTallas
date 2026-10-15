#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory};mkdir -p "$out"
sources=(rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_bank_shell_shared_static.sv rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_bank_memory_shared_static.sv rtl/test/tb_hgi_hc_bank_shell_shared_static.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
for bank in 0 1 2 3 4 5 6 7;do
 iverilog -g2012 -s tb_hgi_hc_bank_shell_shared_static -Ptb_hgi_hc_bank_shell_shared_static.BANK_ID=$bank -o "$out/b$bank.vvp" "${sources[@]}" >"$out/b$bank.compile.log" 2>&1
 vvp "$out/b$bank.vvp" >"$out/b$bank.log" 2>&1
 grep 'BANK_SHELL_SHARED PASS' "$out/b$bank.log"
done
for mode in SLOT ID;do
 arg=-Ptb_hgi_hc_bank_shell_shared_static.MUT=1
 [[ $mode == SLOT ]] || arg=-Ptb_hgi_hc_bank_shell_shared_static.MUT_ID=1
 iverilog -g2012 -s tb_hgi_hc_bank_shell_shared_static "$arg" -o "$out/m$mode.vvp" "${sources[@]}" >"$out/m$mode.compile.log" 2>&1
 set +e
 vvp "$out/m$mode.vvp" >"$out/m$mode.log" 2>&1;rc=$?
 set -e
 [[ $rc != 0 ]];grep 'BANK_SHELL_SHARED.*mismatch' "$out/m$mode.log"
done
