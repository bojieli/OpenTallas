#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../../.." && pwd)
out=$(realpath -m "${1:?output directory}")
mkdir -p "$out"
cp "$root/results/arch/hbm_vm_lg_split_1015/programme/NE_812.hex" "$out/NE_812.hex"
sources=("$here/ot_hbm_vm_lg_static_bank.sv" "$here/ot_hbm_vm_lg_static_split.sv"
 "$here/ot_vms_bank_static.sv" "$here/ot_vms_calendar_static.sv" "$here/hfd_hgi_vm_calendar_static.sv"
 "$root/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
 "$here/tb_hbm_vm_lg_static_programmed.sv")
cd "$out"
for mutant in 0 1;do
  iverilog -g2012 -s tb_hbm_vm_lg_static_programmed -Ptb_hbm_vm_lg_static_programmed.MUT="$mutant" -o "m$mutant" "${sources[@]}" >"m$mutant.compile.log" 2>&1
  if vvp "m$mutant" >"m$mutant.log" 2>&1;then
    [[ "$mutant" == 0 ]] || exit 1
    grep '^VM_LG_PROGRAMMED PASS' "m$mutant.log"
  else
    [[ "$mutant" != 0 ]] || { cat "m$mutant.log";exit 1; }
    grep 'actual bank readback mismatch' "m$mutant.log"
  fi
done
