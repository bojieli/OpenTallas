#!/usr/bin/env bash
set -euo pipefail
cd /work
L=''
for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
yosys -l resynth.log -p "$L read_verilog -lib ot_sram_1r1w_32x128_m1_bb.v; read_verilog qkd_host_native_engine_n32.sv; hierarchy -check -top qkd_host_native_engine_n32; synth -top qkd_host_native_engine_n32 -noabc; write_verilog -noattr resynth.v" > resynth.stdout.log 2>&1
