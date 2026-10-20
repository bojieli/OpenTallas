#!/bin/bash
set -eu
iverilog -g2012 -s tb_sysface_reset32 -o reset32.vvp qfd_sysface_reset32.sv tb_sysface_reset32.sv
vvp reset32.vvp > reset32_current.log
sed 's/assign leaf_n\[32\*g+:N\]=q;/assign leaf_n[32*g+:N]={N{parent_q[g]}};/' qfd_sysface_reset32.sv > reset32_early.sv
iverilog -g2012 -s tb_sysface_reset32 -o reset32_early.vvp reset32_early.sv tb_sysface_reset32.sv
if vvp reset32_early.vvp > reset32_early.log 2>&1; then echo MUTANT_SURVIVED;exit 1;fi
grep -q 'SYSFACE_RESET32 release skew' reset32_early.log
cat reset32_current.log
cat reset32_early.log
echo RESET32_SUITE_PASS
