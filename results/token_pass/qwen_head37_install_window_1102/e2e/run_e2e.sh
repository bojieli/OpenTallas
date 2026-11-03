#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
S="ot_ks_add.sv ot_rom_4096x266_m8.v ot_sram_1r1w_64x512_m1_r2c2.v qfd_dv_calendar_rom.sv qfd_dv_cmd_cal_mu_head37.sv qkd_program_commit.sv qkd_program_pw_observer_p.sv qfd_dv_table_rom_loader.sv qfd_dv_slice_tload.sv tb_ctlm_tload.sv"
sha256sum rom/* dw.hex $S > inputs.sha256
echo "BUILD_START $(date -Is) host=$(hostname -s)" > status
/usr/bin/time -v -o build.time $VL --binary --timing -O0 -finline -j 4 --output-groups 16 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS '-O0 -w -fno-var-tracking' --top-module tb_ctlm_tload $S --Mdir obj > build.log 2>&1
rc=$?; echo BUILD_RC=$rc >> status; [ $rc = 0 ] || exit $rc
/usr/bin/time -v -o run.time ./obj/Vtb_ctlm_tload +OT_ROM_DIR="$PWD/rom" > run.log 2>&1
rc=$?; echo RUN_RC=$rc >> status; grep -q E2E_DONE run.log || exit 3
echo DONE >> status
