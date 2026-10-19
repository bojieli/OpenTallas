#!/usr/bin/env bash
# LH-UNREAD 10-19: hfd_hgi_vm_calendar_f20_role (W 19 / 38 / 89) vs universal hfd_hgi_vm_calendar_f20; MUT 1/2 must FAIL.
set -uo pipefail
cd "$(dirname "$0")/.."
out=$(realpath -m "${1:?out}"); mkdir -p "$out"
M=../../../../../physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
S="ot_static_program_target.sv ot_vms_calendar_static_xcap.sv hfd_hgi_vm_calendar.sv hfd_hgi_vm_calendar_f20.sv hfd_hgi_vm_calendar_f20_role.sv $M fill_universal_0600/tb_vm_calendar_f20_role.sv"
rc=0
for w in 19 38 89; do for m in 0 1 2; do for s in 11 23; do
  iverilog -g2012 -s tb_vm_calendar_f20_role -Ptb_vm_calendar_f20_role.W=$w -Ptb_vm_calendar_f20_role.MUT=$m -Ptb_vm_calendar_f20_role.SEED=$s \
    -o "$out/w${w}m${m}s${s}.vvp" $S > "$out/build_w${w}m${m}s${s}.log" 2>&1 || { echo "BUILD FAIL w$w m$m"; rc=1; continue; }
  vvp "$out/w${w}m${m}s${s}.vvp" > "$out/run_w${w}m${m}s${s}.log" 2>&1; r=$?
  echo "W$w MUT$m SEED$s rc=$r $(grep -h 'CAL_F20_ROLE' "$out/run_w${w}m${m}s${s}.log" | head -1)"
  if [ $m = 0 ]; then [ $r = 0 ] && grep -q 'CAL_F20_ROLE PASS' "$out/run_w${w}m${m}s${s}.log" || rc=1
  else { [ $r != 0 ] && grep -q 'CAL_F20_ROLE FAIL' "$out/run_w${w}m${m}s${s}.log"; } || { echo "W$w MUT$m NOT DETECTED"; rc=1; }; fi
done; done; done
[ $rc = 0 ] && echo "CAL_F20_ROLE GATE PASS" || { echo "CAL_F20_ROLE GATE FAIL"; exit 1; }
