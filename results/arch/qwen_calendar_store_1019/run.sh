#!/bin/bash
set -euo pipefail
src=$PWD/src
vbin=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vbin" --version >verilator.version
for m in 0 1 2 3 4;do
 "$vbin" --binary --timing -Wno-fatal -j 4 --top-module tb_qfd_dv_calendar_rom -GMUT=$m -Mdir obj$m \
 "$src/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v" \
 "$src/rtl/qwen_dv/qfd_dv_calendar_rom.sv" "$src/rtl/test/qwen_dv/tb_qfd_dv_calendar_rom.sv" >build$m.log 2>&1
 set +e
 obj$m/Vtb_qfd_dv_calendar_rom +OT_ROM_DIR=$PWD/image +EXPECTED=$PWD/image/expected.hex >mut$m.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;grep CAL_DATA_MISMATCH mut$m.log;fi
 done
for f in 1 2 3 4 5;do obj0/Vtb_qfd_dv_calendar_rom +OT_ROM_DIR=$PWD/image +EXPECTED=$PWD/image/expected.hex +FAULT=$f >fault$f.log 2>&1;done
