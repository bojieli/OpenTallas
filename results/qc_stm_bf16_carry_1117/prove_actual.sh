#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/fable-fix-qc-hcfe/src/results/qc_stm_bf16_carry_1117
yosys -Q -T -p 'read_verilog -sv -DOT_QFD_BF16_CARRY actual_function_miter.sv; prep -top actual_miter -flatten; sat -verify -prove ok 1 -show b' > actual_proof.log 2>&1
if yosys -Q -T -p 'read_verilog -sv -DOT_QFD_BF16_CARRY actual_function_miter.sv; prep -top actual_miter -flatten; sat -verify -prove mutant_ok 1 -show b' > actual_mutant.log 2>&1;then exit 9;fi
printf 'ACTUAL_FUNCTION_EXACT_PASS MUTANT_CAUGHT\n'
