#!/usr/bin/env bash
# ot_vms_calendar_static (programme SRAM sequencer inside hfd_hgi_vm_calendar_<q>) exact bench, or one named mutant.
# MUT=0 exact; MUT=1 wrong wrap PC; MUT=2 extra cycle at loop boundary (RTL parameter mutants) -- HBM-V15-HARDEN 10-15
set -euo pipefail
out=${1:?out}; mut=${2:-0}; mkdir -p "$out"
d=rtl/hbm_accel/generic/vm/static
macro=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
iverilog -g2012 -s tb_vms_calendar_static -Ptb_vms_calendar_static.MUT="$mut" -o "$out/sim.vvp" $d/ot_vms_calendar_static.sv "$macro" $d/tb_vms_calendar_static.sv
vvp "$out/sim.vvp" > "$out/sim.log" 2>&1; rc=$?
cat "$out/sim.log"
[ $rc -eq 0 ] && ! grep -q 'Fatal\|FAIL' "$out/sim.log"
