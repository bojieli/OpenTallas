#!/bin/bash
# bench: old qfd_dv_sram_delay vs new orq, D in 3,4,14; mutants 1,2.
cd /srv/opentallas-scratch2/claude/qct12/sta
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
R=/srv/opentallas-scratch2/claude/qct12/repo
for cfg in "3 512 0" "4 512 0" "14 514 0" "3 512 1" "3 512 2"; do set -- $cfg; D=$1 W=$2 M=$3; o=obj_${D}_${M}; rm -rf $o;
 $V --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTITOP --x-assign unique --x-initial unique --top-module tb_orq -GD=$D -GW=$W -GMUT=$M --Mdir $o sva_stub.sv tb_orq.sv $R/rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv > ${o}.build.log 2>&1 || { echo BUILD_FAIL $o; tail -5 ${o}.build.log; continue; }
 ./$o/Vtb_orq +verilator+seed+7 +verilator+rand+reset+2 2>&1 | tail -4 | cut -c1-200
done
