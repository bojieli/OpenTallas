#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch2/claude/codex-res2-native-1101/gate1
cd "$R"
sha256sum -c packet.sha256 > input_guard.log 2>&1 || { echo SOURCE_GUARD_FAIL >status; exit 3; }
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
echo "BUILD_START $(date -Is) host=$(hostname -s)" >status
/usr/bin/time -v -o build.time "$VL" --binary --timing -j 1 -O0 -finline -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' $(cat defines.f) +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM --top-module tb_mu_native -f source.f --Mdir obj >build.log 2>&1
rc=$?;echo "BUILD_RC=$rc $(date -Is)" >>status
[ "$rc" = 0 ] || exit "$rc"
/usr/bin/time -v -o base.time ./obj/Vtb_mu_native >base.log 2>&1
rc=$?;echo "BASE_RC=$rc" >>status
[ "$rc" = 0 ] && grep -q NATIVE_RES2_PASS base.log || exit 1
for mode in MUT_OLD_CALLER MUT_SCALE MUT_USER; do
 ./obj/Vtb_mu_native +"$mode" >"$mode.log" 2>&1
 rc=$?;echo "$mode=$rc" >>status
 [ "$rc" != 0 ] && grep -Eq 'RES2_PAYLOAD_MISMATCH|RES2_WRONG_USER_OR_ADDRESS' "$mode.log" || exit 2
done
echo PASS_NATIVE_RES2_COMPONENT >>status
