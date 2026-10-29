#!/bin/bash
set -euo pipefail
repo=${1:?repo}; out=${2:?out}; mkdir -p "$out"
r=$repo/results/hbm_calendar_1029/oneclk
s=$repo/rtl/hbm_accel/generic/vm/static
m=$repo/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for mode in 0 1 2; do
 top=$r/hfd_hgi_vm_calendar_f20_oneclk.sv
 [ "$mode" != 2 ] || top=$r/hfd_hgi_vm_calendar_f20_oneclk_wrongclk.sv
 iverilog -g2012 -s tb_vm_calendar_f20_eq -Ptb_vm_calendar_f20_eq.MUT=$mode -o "$out/m$mode.vvp" "$s/ot_static_program_target.sv" "$s/ot_vms_calendar_static_xcap.sv" "$s/hfd_hgi_vm_calendar.sv" "$top" "$m" "$r/tb_calendar_oneclk.sv" > "$out/build$mode.log" 2>&1
 set +e; vvp "$out/m$mode.vvp" > "$out/run$mode.log" 2>&1; rc=$?; set -e
 grep CAL_F20_EQ "$out/run$mode.log"
 if [ "$mode" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
done
echo CALENDAR_ONECLK_GATE_PASS
