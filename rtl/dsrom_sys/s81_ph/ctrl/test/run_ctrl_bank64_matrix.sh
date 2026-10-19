#!/bin/bash
set -u
base=${1:?absolute output}
mkdir -p "$base"
verilator --version
failed=0
for x in 340:0:base 340:180:base 340:720:base 277:0:base 277:180:base 277:720:base 340:0:current 340:0:emptyread;do
 IFS=: read -r w phase mut <<<"$x"
 o="$base/fifo/w${w}_p${phase}_${mut}";mkdir -p "$o"
 defs=(-DS81CTRL_SRAM_BANK64)
 [ "$mut" != current ] || defs+=(-DS81CTRL_SRAM_MUT_CURRENT)
 [ "$mut" != emptyread ] || defs+=(-DS81CTRL_SRAM_MUT_EMPTYREAD)
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_ctrl_fifo_sram -GW="$w" -GPHASE="$phase" "${defs[@]}" --Mdir "$o/obj" rtl/dsrom_sys/s81_ph/ctrl/test/tb_ctrl_fifo_sram.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v >"$o/build.log" 2>&1
 brc=$?;echo "$brc" >"$o/build_rc"
 if [ "$brc" != 0 ];then echo "BANK64 BUILD_FAIL $x";failed=1;continue;fi
 "$o/obj/Vtb_ctrl_fifo_sram" >"$o/run.log" 2>&1;rc=$?;echo "$rc" >"$o/exit_code"
 if [ "$mut" = base ];then
  if [ "$rc" != 0 ] || ! grep -q 'CTRL_FIFO_EXACT PASS' "$o/run.log";then failed=1;fi
 else
  if [ "$rc" = 0 ] || ! grep -qE 'errors3314|CTRL_SRAM_FIFO_COLLISION' "$o/run.log";then failed=1;fi
 fi
 tail -n 4 "$o/run.log"
done
for m in none KRDY RD PACK;do
 S81CTRL_BANK64=1 bash rtl/dsrom_sys/s81_ph/ctrl/test/run_ctrl_pcr_min.sh "$base/pcr_${m,,}" sram "$m" || failed=1
done
echo "BANK64_MATRIX_STATUS $failed"
exit "$failed"
