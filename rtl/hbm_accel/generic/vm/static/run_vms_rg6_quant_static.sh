#!/usr/bin/env bash
set -euo pipefail
out="${1:?output directory}";inputs="${2:-.}"
mkdir -p "$out"
for mut in 0 1 2;do
 /usr/bin/time -v -o "$out/compile-$mut.time" iverilog -g2012 -s tb_vms_rg6_quant_static -Ptb_vms_rg6_quant_static.MUT="$mut" -o "$out/gate-$mut.vvp" "$inputs/tb_vms_rg6_quant_static.sv" "$inputs/hfd_vms_bank_static_rg6wg2.sv" "$inputs/ot_vms_bank_static.sv" "$inputs/ot_sram_1r1w_1024x256_m2_r2c2.v" > "$out/compile-$mut.log" 2>&1
 set +e
 /usr/bin/time -v -o "$out/sim-$mut.time" vvp "$out/gate-$mut.vvp" > "$out/sim-$mut.log" 2>&1
 rc=$?
 set -e
 cat "$out/sim-$mut.log"
 if [[ $mut == 0 ]];then [[ $rc == 0 ]];grep -q 'VM_RG6_QUANT_STATIC PASS' "$out/sim-$mut.log"
 elif [[ $mut == 1 ]];then [[ $rc != 0 ]];grep -q 'actual bank response group mismatch' "$out/sim-$mut.log"
 else [[ $rc != 0 ]];grep -q 'actual WG1 write owner mismatch' "$out/sim-$mut.log";fi
done
printf 'PASS literal RG6/WG2 SID0 actual24SRAM +WG1/allwriteowners and actual response/writeowner mutants\n'
