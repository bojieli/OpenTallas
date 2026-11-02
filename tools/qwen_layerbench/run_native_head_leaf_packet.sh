#!/usr/bin/env bash
# REVIEW REQUIRED before normal ot-run admission. Immutable finite component.
set -uo pipefail
cd "$(dirname "$0")"
sha256sum -c packet.sha256 >input_guard.log 2>&1 || exit 3
python3 prepare_mutant.py >prepare.log 2>&1 || exit 4
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
export CXX=/usr/bin/g++
"$VL" --version >toolchain.log
/usr/bin/g++ --version >>toolchain.log
printf 'START host=%s\n' "$(hostname -s)" >status
/usr/bin/time -v -o build.time "$VL" --binary --timing -O0 -finline --output-groups 16 -j 1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS '-O0 -w -fno-var-tracking' --top-module tb_native_head_leaf -f source.f native_tile0_cut.sv tb_native_head_leaf.sv --Mdir obj >build.log 2>&1
rc=$?;echo "BUILD_RC=$rc" >>status
[ "$rc" = 0 ] || exit "$rc"
/usr/bin/time -v -o baseline.time ./obj/Vtb_native_head_leaf +OT_ROM_DIR=rom >baseline.log 2>&1
rc=$?;echo "BASELINE_RC=$rc" >>status
[ "$rc" = 0 ] && grep -q NATIVE_HEAD_LEAF_PASS baseline.log || exit 1
/usr/bin/time -v -o wrong_weight.time ./obj/Vtb_native_head_leaf +OT_ROM_DIR=rom_wrong_weight >wrong_weight.log 2>&1
rc=$?;echo "WRONG_WEIGHT_RC=$rc" >>status
[ "$rc" != 0 ] && grep -q 'actual=c32f0600 expected=c3312600' wrong_weight.log || exit 2
echo PASS_NATIVE_HEAD_LEAF_RAW_COMPONENT >>status
