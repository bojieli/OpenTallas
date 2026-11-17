#!/bin/bash
set -uo pipefail
ulimit -c 0
cd "$(dirname "$0")"
case "${HEAD_BAD_REPLY:-0}" in 0) tag=baseline;; 1) tag=old_reply;; *) exit 2;; esac
mkdir "$tag" || { echo REFUSE_EXISTING_RUN;exit 3; }
sha256sum -c packet.sha256 >"$tag/input_guard.log" 2>&1 || { echo SOURCE_GUARD_FAIL >"$tag/status";exit 3; }
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
echo "BUILD_START $(date -Is) host=$(hostname -s)" >"$tag/status"
/usr/bin/time -v -o "$tag/build.time" "$VL" --binary --timing -j 1 -O0 -finline --output-groups 64 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' $(cat defines.f) -GHEAD_BAD_REPLY=${HEAD_BAD_REPLY:-0} --top-module tb_mu_native -f source.f --Mdir "$tag/obj" >"$tag/build.log" 2>&1
rc=$?;echo "BUILD_RC=$rc $(date -Is)" >>"$tag/status"
[ "$rc" = 0 ] || exit "$rc"
/usr/bin/time -v -o "$tag/base.time" ./"$tag"/obj/Vtb_mu_native >"$tag/base.log" 2>&1
rc=$?;echo "BASE_RC=$rc" >>"$tag/status"
if [ "${HEAD_BAD_REPLY:-0}" = 1 ];then
 [ "$rc" != 0 ] && grep -Eq 'HEAD_NATIVE_VALUE|HEAD_WRONG_OUTPUT_ADDR|HEAD_BF16_VALUE|HEAD_COVERAGE' "$tag/base.log" || exit 2
 echo CAUGHT_OLD_HEAD_REPLY_PROFILE >>"$tag/status";exit 0
fi
[ "$rc" = 0 ] && grep -q NATIVE_HEAD_APPLY_PASS "$tag/base.log" || exit 1
for mode in MUT_GAIN MUT_RAW_X MUT_USER;do
 ./"$tag"/obj/Vtb_mu_native +"$mode" >"$tag/$mode.log" 2>&1
 rc=$?;echo "$mode=$rc" >>"$tag/status"
 [ "$rc" != 0 ] && grep -Eq 'HEAD_NATIVE_VALUE|HEAD_WRONG_OUTPUT_ADDR|HEAD_BF16_VALUE' "$tag/$mode.log" || exit 2
done
echo PASS_NATIVE_HEAD_APPLY_COMPONENT >>"$tag/status"
