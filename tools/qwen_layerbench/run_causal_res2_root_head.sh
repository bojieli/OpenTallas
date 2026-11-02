#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c packet.sha256 >input_guard.log
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o build.time "$VL" --binary --timing -j 1 -O0 -finline -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' $(cat defines.f) +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM --top-module tb_causal -f source.f --Mdir obj >build.log 2>&1
/usr/bin/time -v -o base.time ./obj/Vtb_causal >base.log 2>&1
grep -q NATIVE_CAUSAL_RES2_ROOT_HEAD_PASS base.log
for mode in MUT_OLD_CALLER MUT_DROP_PARTIAL MUT_DROP_RSTD; do
 set +e
 ./obj/Vtb_causal +"$mode" >"$mode.log" 2>&1
 rc=$?
 set -e
 [ "$rc" != 0 ]
 case "$mode" in
 MUT_OLD_CALLER) grep -Eq 'CAUSAL_VALUE|NATIVE_PARTIAL_VALUE' "$mode.log";;
 MUT_DROP_PARTIAL) grep -q ROOT_COMPLETION "$mode.log";;
 MUT_DROP_RSTD) grep -q CAUSAL_VALUE "$mode.log";;
 esac
done
echo PASS_NATIVE_CAUSAL_COMPONENT >status
