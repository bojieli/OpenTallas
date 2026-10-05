#!/bin/bash
set -u
iverilog -g2012 -s tb_hdc_bf16_capture_split -o gate.vvp rtl/test/tb_hdc_bf16_capture_split.sv rtl/hdc/v41x/ot_hdc_bf16_capture_split.sv rtl/hdc/ot_hdc_prefix.sv > compile.log 2>&1
rc=$?
if [ "$rc" = 0 ]; then vvp gate.vvp > runtime.log 2>&1; rc=$?; fi
printf "%s\n" "$rc" > terminal.rc
exit "$rc"
