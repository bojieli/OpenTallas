#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
sha256sum -c packet.sha256 >input_guard.log 2>&1 || { echo SOURCE_GUARD_FAIL >status;exit 3; }
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
echo "BUILD_START $(date -Is) host=$(hostname -s)" >status
/usr/bin/time -v -o build.time "$VL" --binary --timing -O0 -finline -j 1 --output-groups 16 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS '-O0 -w -fno-var-tracking' -f source.f --top-module tb_head_ctlm37 --Mdir obj >build.log 2>&1
rc=$?;echo "BUILD_RC=$rc $(date -Is)" >>status
[ "$rc" = 0 ] || exit "$rc"
/usr/bin/time -v -o base.time ./obj/Vtb_head_ctlm37 +OT_ROM_DIR=rom >base.log 2>&1
rc=$?;echo "BASE_RC=$rc" >>status
[ "$rc" = 0 ] && grep -q NATIVE_CTLM37_PASS base.log || exit 1
./obj/Vtb_head_ctlm37 +OT_ROM_DIR=rom +MUT_USER >MUT_USER.log 2>&1
rc=$?;echo "MUT_USER=$rc" >>status
[ "$rc" != 0 ] && grep -q CTLM_WRONG_REQUEST MUT_USER.log || exit 2
echo PASS_NATIVE_CTLM37_COMPONENT >>status
