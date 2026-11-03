#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
sha256sum rom/* head37_stage.json user_relocation.json loader_main.sv reference.sv rom.v tb.sv check.py > inputs.sha256
echo "BUILD_START $(date -Is) host=$(hostname -s)" >status
/usr/bin/time -v -o build.time $VL --binary --timing -j 1 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_loader_real rom.v loader_main.sv reference.sv tb.sv -Mdir obj >build.log 2>&1
rc=$?;echo BUILD_RC=$rc >>status;[ $rc = 0 ] || exit $rc
/usr/bin/time -v -o base.time ./obj/Vtb_loader_real +OT_ROM_DIR="$PWD/rom" >base.log 2>&1
rc=$?;echo BASE_RC=$rc >>status;[ $rc = 0 ] || exit $rc
python3 check.py base.log head37_stage.json user_relocation.json result.json >check.log 2>&1;rc=$?;echo CHECK_RC=$rc >>status;[ $rc = 0 ] || exit 1
./obj/Vtb_loader_real +OT_ROM_DIR="$PWD/rom" +MUT_GAIN >MUT_GAIN.log 2>&1;echo MUT_GAIN_SIM=$? >>status
python3 check.py MUT_GAIN.log head37_stage.json user_relocation.json mut_result.json >mut_check.log 2>&1;rc=$?;echo MUT_GAIN_CHECK=$rc >>status
[ $rc != 0 ] || exit 2
echo PASS_LOADER_REAL_PAYLOAD >>status
