#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-token-1101/mu_calendar1340
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
cd "$R/portable"
echo BUILD_START_BOOT_SETID_FIX > "$R/status2"
set +e
/usr/bin/time -v -o "$R/build2.time" "$VL" --binary --timing -j 1 -O0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' $(cat defines.f) --top-module tb_mu_native -f source.f --Mdir "$R/obj" > "$R/build2.log" 2>&1
rc=$?;echo BUILD_RC_$rc >> "$R/status2";[ "$rc" = 0 ] || exit "$rc"
"$R/obj/Vtb_mu_native" +OT_ROM_DIR="$R/portable" > "$R/base2.log" 2>&1
rc=$?;echo BASE_RC_$rc >> "$R/status2";[ "$rc" = 0 ] || exit "$rc"
grep -q MU_CALENDAR_NATIVE_XA_PASS "$R/base2.log" || exit 4
for mode in MUT_PAYLOAD MUT_PIDX; do
 "$R/obj/Vtb_mu_native" +OT_ROM_DIR="$R/portable" +"$mode" > "$R/${mode}2.log" 2>&1
 rc=$?
 pattern=MU_PAYLOAD_MISMATCH
 [ "$mode" = MUT_PIDX ] && pattern=LIVE_SU_PIDX
 if [ "$rc" = 0 ] || ! grep -q "$pattern" "$R/${mode}2.log"; then echo CONTROL_FAIL_$mode >> "$R/status2";exit 3;fi
 echo CONTROL_CAUGHT_$mode >> "$R/status2"
done
"$R/obj/Vtb_mu_native" +OT_ROM_DIR="$R/wrong_a" > "$R/MUT_A2.log" 2>&1
rc=$?
if [ "$rc" = 0 ] || ! grep -q MU_PAYLOAD_MISMATCH "$R/MUT_A2.log"; then echo CONTROL_FAIL_MUT_A >> "$R/status2";exit 3;fi
echo CONTROL_CAUGHT_MUT_A >> "$R/status2"
echo PASS >> "$R/status2"
