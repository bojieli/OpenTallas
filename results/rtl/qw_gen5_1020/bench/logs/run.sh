#!/bin/bash
# QW-GEN5 qfd_ckdiv6 bench + div5 mutant on the daemon Verilator 5.050 and iverilog (fleet)
cd ${1:?bench dir}
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; $VL --version
$VL --binary --timing -Wno-fatal -Wno-DECLFILENAME --top-module tb -Mdir obj_pass qfd_ckdiv6.sv tb_qfd_ckdiv6.sv > build_pass.log 2>&1 && ./obj_pass/Vtb > pass.log 2>&1; tail -2 pass.log
$VL --binary --timing -Wno-fatal -Wno-DECLFILENAME -DQFD_CKDIV6_MUT_DIV5 --top-module tb -Mdir obj_mut qfd_ckdiv6.sv tb_qfd_ckdiv6.sv > build_mut.log 2>&1 && ./obj_mut/Vtb > mut_div5.log 2>&1; tail -2 mut_div5.log
iverilog -g2012 -s tb -o iv qfd_ckdiv6.sv tb_qfd_ckdiv6.sv && vvp iv > iv_pass.log; tail -1 iv_pass.log
