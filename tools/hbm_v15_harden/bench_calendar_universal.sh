#!/usr/bin/env bash
# ONE VM calendar master hfd_hgi_vm_calendar: exact programme playback for all four quadrants + reset release window.
# mut 0 exact; 1 reset synchroniser bypassed (RMUT=1); 2 one field offset shifted (bank_client); 3 core MUT=2 extra edge
set -euo pipefail
out=${1:?out}; mut=${2:-0}; mkdir -p "$out"; out=$(realpath "$out")
d=rtl/hbm_accel/generic/vm/static
macro=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
cp $d/hfd_hgi_vm_calendar.sv "$out/cal.sv"; cp $d/ot_vms_calendar_static.sv "$out/core.sv"
rm=0
case "$mut" in
 1) rm=1;;
 2) sed -i 's/assign bank_client=calendar\[33+:24\]/assign bank_client=calendar[34+:24]/' "$out/cal.sv";;
 3) sed -i 's/parameter integer MUT=0/parameter integer MUT=2/' "$out/core.sv";;
esac
if [ "$mut" = 2 ] || [ "$mut" = 3 ]; then cmp -s "$out/cal.sv" $d/hfd_hgi_vm_calendar.sv && cmp -s "$out/core.sv" $d/ot_vms_calendar_static.sv && { echo MUTANT_NOT_APPLIED; exit 3; }; fi
iverilog -g2012 -s tb_vm_calendar_universal -Ptb_vm_calendar_universal.RMUT=$rm -o "$out/sim.vvp" "$out/core.sv" "$out/cal.sv" "$macro" $d/tb_vm_calendar_universal.sv
for q in SW SE NW NE; do
  python3 tools/hbm_v15_harden/gen_calendar_universal.py $q "$out/$q" 40 3
  (cd "$out/$q" && vvp "$out/sim.vvp" > sim.log 2>&1) || true
  cat "$out/$q/sim.log"
  grep -q '^VM_CALENDAR_UNIVERSAL PASS' "$out/$q/sim.log" || { echo "CALUNI FAIL quadrant $q"; exit 1; }
done
echo "VM_CALENDAR_UNIVERSAL_ALL PASS4 quadrants"
