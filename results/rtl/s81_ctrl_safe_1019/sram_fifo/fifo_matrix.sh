#!/bin/bash
set -u
verilator --version
mkdir -p fifo_runs_v2
for x in 340:0:base 340:180:base 340:720:base 277:0:base 277:180:base 277:720:base 340:0:current 340:0:emptyread; do
 IFS=: read -r width phase mut <<< "$x"
 out="$PWD/fifo_runs_v2/w${width}_p${phase}_${mut}"
 mkdir -p "$out"
 defs=()
 if [[ "$mut" == current ]];then defs+=(+define+S81CTRL_SRAM_MUT_CURRENT);fi
 if [[ "$mut" == emptyread ]];then defs+=(+define+S81CTRL_SRAM_MUT_EMPTYREAD);fi
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_ctrl_fifo_sram -GW="$width" -GPHASE="$phase" "${defs[@]}" --Mdir "$out/obj" rtl/dsrom_sys/s81_ph/ctrl/test/tb_ctrl_fifo_sram.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v > "$out/build.log" 2>&1
 brc=$?
 if [[ $brc != 0 ]];then echo "$x BUILD_FAIL $brc";echo "$brc" > "$out/build_rc";continue;fi
 "$out/obj/Vtb_ctrl_fifo_sram" > "$out/run.log" 2>&1
 echo "$?" > "$out/run_rc"
 tail -2 "$out/run.log"
done
