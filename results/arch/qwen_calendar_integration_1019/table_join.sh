#!/bin/bash
set -euo pipefail
cd run
python3 ../src/tools/qwen_layerbench/finite_calendar_body.py --input body.json --out image_load
cp image_load/calendar_m*.viamap.hex tables/
s=../src
vbin=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
sources=("$s/rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv" "$s/rtl/qwen_dv/qfd_dv_calendar_rom.sv"
 "$s/rtl/qwen_dv/qfd_dv_table_rom_loader.sv" "$s/rtl/qwen_dv/qfd_dv_vm.sv"
 "$s/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv"
 "$s/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v"
 "$s/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
 "$s/rtl/test/qwen_dv/tb_qfd_dv_calendar_table_join.sv")
for macro in ot_sram_1r1w_1024x256_m2_r2c2 ot_sram_1r1w_128x256_m1_r2c2 ot_sram_1r1w_256x256_m2_r2c2;do
 sources+=("$s/physical/asap7_memory_macros/$macro/$macro.v")
done
sha256sum "${sources[@]}" > table_join.sources
for m in 0 2 collision early;do
 flags=(); if [ "$m" = collision ];then flags=(-GCOLLIDE=1);elif [ "$m" = early ];then flags=(-GEARLY=1);else flags=(-GLMUT=$m);fi
 "$vbin" --binary --timing -Wno-fatal -j 4 --top-module tb_qfd_dv_calendar_table_join "${flags[@]}"   -Mdir "table_obj$m" "${sources[@]}" > "table_build$m.log" 2>&1
 set +e
 "table_obj$m/Vtb_qfd_dv_calendar_table_join" "+OT_ROM_DIR=$PWD/tables" "+EXPECTED=$PWD/tables/expected.hex"   "+DW=$PWD/image_load/dw.hex" "+PRELOAD=$PWD/image_load/preload_first.hex" > "table_mut$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;grep CALENDAR_TABLE_NATIVE_JOIN_PASS "table_mut$m.log"
  python3 window_check.py > window_check.log
  cp table_windows.trace table_windows_positive.trace
 else test "$rc" != 0
  if [ "$m" = collision ];then grep TABLE_STORE_UNEXPECTED_FAULT "table_mut$m.log"
  elif [ "$m" = early ];then grep TABLE_STORE_CROM_MISMATCH "table_mut$m.log"
  else grep TABLE_STORE_PROG_MISMATCH "table_mut$m.log";fi
 fi
done
