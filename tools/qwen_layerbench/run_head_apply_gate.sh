#!/bin/bash
# A single normal ot-run payload; execute in its immutable packet directory.
set -uo pipefail
cd "$(dirname "$0")"
sha256sum -c packet.sha256 >input_guard.log 2>&1 || { echo SOURCE_GUARD_FAIL >status;exit 3; }
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
echo "BUILD_START $(date -Is) host=$(hostname -s)" >status
# Completed same-body RES2 measurement:14.16GB peak,29m44s with one huge grouped CPP.
# Keep j1/16GB;64 output groups split that giant translation unit without RTL changes.
/usr/bin/time -v -o build.time "$VL" --binary --timing -j 1 -O0 -finline --output-groups 64 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' $(cat defines.f) +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM --top-module tb_mu_native -f source.f --Mdir obj >build.log 2>&1
rc=$?;echo "BUILD_RC=$rc $(date -Is)" >>status
[ "$rc" = 0 ] || exit "$rc"
/usr/bin/time -v -o base.time ./obj/Vtb_mu_native >base.log 2>&1
rc=$?;echo "BASE_RC=$rc" >>status
[ "$rc" = 0 ] && grep -q NATIVE_HEAD_APPLY_PASS base.log || exit 1
for mode in MUT_GAIN MUT_RAW_X MUT_USER;do
 ./obj/Vtb_mu_native +"$mode" >"$mode.log" 2>&1
 rc=$?;echo "$mode=$rc" >>status
 [ "$rc" != 0 ] && grep -Eq 'HEAD_NATIVE_VALUE|HEAD_WRONG_OUTPUT_ADDR|HEAD_BF16_VALUE' "$mode.log" || exit 2
done
echo PASS_NATIVE_HEAD_APPLY_COMPONENT >>status
