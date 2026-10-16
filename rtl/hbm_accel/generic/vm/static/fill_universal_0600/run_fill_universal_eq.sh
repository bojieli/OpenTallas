#!/usr/bin/env bash
# H-NETLIST 0600: universal VM calendar (closed hfd_hgi_vm_calendar) == fill calendar W89 on every edge; mutants 1/2 FAIL.
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
out=$(realpath -m "${1:?out}"); mkdir -p "$out"
D=rtl/hbm_accel/generic/vm/static
M=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
rc=0
for m in 0 1 2; do
  iverilog -g2012 -s tb_fill_calendar_universal_eq -Ptb_fill_calendar_universal_eq.MUT=$m -o "$out/m$m.vvp" \
    $D/ot_vms_calendar_static.sv $D/ot_vms_calendar_static_xcap.sv $D/hfd_hgi_vm_calendar.sv "$M" \
    $D/fill_universal_0600/tb_fill_calendar_universal_eq.sv > "$out/build$m.log" 2>&1
  set +e; vvp "$out/m$m.vvp" > "$out/run$m.log" 2>&1; r=$?; set -e
  grep FILL_UNIVERSAL_EQ "$out/run$m.log" | sed "s/^/MUT$m /"
  if [ $m = 0 ]; then [ $r = 0 ] && grep -q "EQ PASS" "$out/run$m.log" || rc=1; else [ $r != 0 ] || { echo "MUT$m NOT DETECTED"; rc=1; }; fi
done
[ $rc = 0 ] && echo "FILL_UNIVERSAL_EQ GATE PASS" || { echo "FILL_UNIVERSAL_EQ GATE FAIL"; exit 1; }
