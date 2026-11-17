#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/fable-fix-qc-hcfe/src/results/qc_stm_bf16_carry_1117
yosys -Q -T -p 'read_verilog -sv miter.sv; prep -top miter; sat -verify -prove ok 1 -show b' > proof.log 2>&1
if yosys -Q -T -p 'read_verilog -sv miter.sv; prep -top miter; sat -verify -prove mutant_ok 1 -show b' > mutant.log 2>&1;then exit 9;fi
printf 'EXACT_PASS MUTANT_CAUGHT\n'
