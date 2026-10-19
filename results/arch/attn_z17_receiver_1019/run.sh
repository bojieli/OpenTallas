#!/bin/bash
set -euo pipefail
printf 'REAL_SIM_START '; date -u --iso-8601=seconds
iverilog -V > iverilog.version.log 2>&1
iverilog -g2012 -s tb -o receiver.vvp qkd_native_attention_static_ctl.sv qkd_native_attention_static_ctl_z17.sv tb_receiver_z17.sv > compile.log 2>&1
vvp receiver.vvp > simulation.log 2>&1
cat simulation.log
printf 'REAL_SIM_EXIT 0 '; date -u --iso-8601=seconds
