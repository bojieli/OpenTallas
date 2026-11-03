#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
sha256sum rom/* rom.v qfd_dv_slice_tload.sv qfd_dv_table_rom_loader.sv tb_tload_win.sv > inputs.sha256
echo "BUILD_START $(date -Is) host=$(hostname -s)" > status
$VL --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_tload_win rom.v qfd_dv_table_rom_loader.sv qfd_dv_slice_tload.sv tb_tload_win.sv -Mdir obj > build.log 2>&1
rc=$?; echo BUILD_RC=$rc >> status; [ $rc = 0 ] || exit $rc
/usr/bin/time -v -o run.time ./obj/Vtb_tload_win +OT_ROM_DIR="$PWD/rom" > run.log 2>&1
rc=$?; echo RUN_RC=$rc >> status; grep -q TB_DONE run.log || exit 3
echo DONE >> status
