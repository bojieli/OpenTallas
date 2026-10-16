#!/usr/bin/env bash
# H-NETLIST 0600: hfd_hgi_vm_calendar_f20 (folded F20 target, strap tgt) == programme target + universal calendar, every edge.
set -euo pipefail
cd "$(dirname "$0")/.."
out=$(realpath -m "${1:?out}"); mkdir -p "$out"
M=../../../../../physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
rc=0
for m in 0 1; do
  iverilog -g2012 -s tb_vm_calendar_f20_eq -Ptb_vm_calendar_f20_eq.MUT=$m -o "$out/m$m.vvp" ot_static_program_target.sv \
    ot_vms_calendar_static_xcap.sv hfd_hgi_vm_calendar.sv hfd_hgi_vm_calendar_f20.sv "$M" fill_universal_0600/tb_vm_calendar_f20_eq.sv > "$out/build$m.log" 2>&1
  set +e; vvp "$out/m$m.vvp" > "$out/run$m.log" 2>&1; r=$?; set -e
  grep CAL_F20_EQ "$out/run$m.log" | sed "s/^/MUT$m /"
  if [ $m = 0 ]; then [ $r = 0 ] || rc=1; else [ $r != 0 ] || { echo "MUT$m NOT DETECTED"; rc=1; }; fi
done
[ $rc = 0 ] && echo "CAL_F20_EQ GATE PASS" || { echo "CAL_F20_EQ GATE FAIL"; exit 1; }
