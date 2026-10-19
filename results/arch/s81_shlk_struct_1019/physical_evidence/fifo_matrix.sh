#!/bin/bash
set -uo pipefail
cd src
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
U=rtl/dsrom_sys/s81_dv/unit/host_sram
M=physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v
mkdir -p ../fifo
$VL --version > ../fifo/verilator.version
bad=0
for x in 514:4:0:base 514:4:173:base 514:4:511:base 289:4:0:base 289:3:173:base 289:3:511:base 514:4:0:current 514:4:0:emptyread; do
 IFS=: read -r w aw ph mode <<< "$x"
 o=../fifo/w${w}_aw${aw}_p${ph}_${mode};mkdir -p "$o";o=$(realpath "$o")
 defs=();[ "$mode" != current ] || defs+=(-DS81SH_SRAM_MUT_CURRENT);[ "$mode" != emptyread ] || defs+=(-DS81SH_SRAM_MUT_EMPTYREAD)
 $VL --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_sh_host_fifo -GW="$w" -GAW="$aw" -GPHASE="$ph" "${defs[@]}" --Mdir "$o/obj" "$U/tb_sh_host_fifo.sv" "$U/ot_dsdv_host_afifo_sram.sv" "$M" > "$o/build.log" 2>&1
 if [ $? != 0 ];then echo "$x BUILDFAIL";bad=1;continue;fi
 "$o/obj/Vtb_sh_host_fifo" > "$o/run.log" 2>&1;rc=$?;echo "$rc" > "$o/run_rc";tail -3 "$o/run.log"
 if [ "$mode" = base ];then [ "$rc" = 0 ] || bad=1;else [ "$rc" != 0 ] || bad=1;fi
done
exit "$bad"
