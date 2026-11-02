#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
sha256sum -c packet.sha256 >input_guard.log 2>&1 || { echo SOURCE_GUARD_FAIL >status;exit 3; }
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
echo "BUILD_START $(date -Is) host=$(hostname -s)" >status
/usr/bin/time -v -o build.time "$VL" --binary --timing -O0 -finline -j 1 --output-groups 64 --output-split 10000 --output-split-cfuncs 1000 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS '-O0 -w -fno-var-tracking' -f defines.f -f source.f --top-module tb_native_root --Mdir obj >build.log 2>&1
rc=$?;echo "BUILD_RC=$rc $(date -Is)" >>status
[ "$rc" = 0 ] || exit "$rc"
for mode in PREARM LEGACY_AMNB0;do
 args=();[ "$mode" = PREARM ] || args=(+"$mode")
 /usr/bin/time -v -o "$mode.time" ./obj/Vtb_native_root "${args[@]}" >"$mode.log" 2>&1
 rc=$?;echo "$mode=$rc" >>status
 [ "$rc" = 0 ] && grep -q NATIVE_PREARM_ROOT_PASS "$mode.log" || exit 1
done
# Publication bits and cfg-to-write edges must match, not just pass separately.
diff <(grep 'NATIVE_ROOT_CASE user' PREARM.log) <(grep 'NATIVE_ROOT_CASE user' LEGACY_AMNB0.log) >rstd_noninterference.diff || exit 4
for mode in COLLECT_CFG LATE_CFG MUT_AMAX_USER;do
 ./obj/Vtb_native_root +"$mode" >"$mode.log" 2>&1
 rc=$?;echo "$mode=$rc" >>status
 [ "$rc" != 0 ] && grep -Eq 'ROOT_OUTPUT_ADDRESS|ROOT_RSTD_BITS|NO_NATIVE_RSTD|NATIVE_ROOT_FAULT' "$mode.log" || exit 2
done
echo PASS_NATIVE_ROOT_PREARM_COMPONENT >>status
