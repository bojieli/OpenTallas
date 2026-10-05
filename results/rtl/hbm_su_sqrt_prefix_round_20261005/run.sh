#!/bin/bash
set -u
iverilog -V > toolchain.log 2>&1
iverilog -g2012 -DOT_HDC_SQRT_PREFIX_ROUND=1 -s clock_top -o gate.vvp clock.sv rtl/test/tb_hdc_fsqrt_equiv.sv rtl/hdc/v41/ot_hdc_fsqrt_prefix_round.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_sfu.sv rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv > compile.log 2>&1
rc=$?
if [ "$rc" = 0 ]; then vvp gate.vvp +N=4096 > runtime.log 2>&1; rc=$?; fi
printf "%s\n" "$rc" > terminal.rc
exit "$rc"
