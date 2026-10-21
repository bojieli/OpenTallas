#!/bin/bash
cd /srv/opentallas-scratch/claude/qw-grt5/bench
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; $VL --version
$VL --binary --timing -Wno-fatal -Wno-DECLFILENAME --top-module tb -Mdir obj_pass qfd_fault_or.sv tb_qfd_fault_or.sv > build_pass.log 2>&1 && ./obj_pass/Vtb > pass.log 2>&1; tail -2 pass.log
$VL --binary --timing -Wno-fatal -Wno-DECLFILENAME -DQFD_FAULT_OR_MUT_NOSTICKY --top-module tb -Mdir obj_mut qfd_fault_or.sv tb_qfd_fault_or.sv > build_mut.log 2>&1 && ./obj_mut/Vtb > mut_nosticky.log 2>&1; tail -2 mut_nosticky.log
iverilog -g2012 -s tb -o iv qfd_fault_or.sv tb_qfd_fault_or.sv && vvp iv > iv_pass.log; tail -1 iv_pass.log
