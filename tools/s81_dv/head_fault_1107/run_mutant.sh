#!/bin/bash
set -u
cd "$(dirname "$0")"
obj/Vhead_guard_tb +SHIFT4 > TT_shift4.log 2>&1
rc=$?; echo "$rc" > TT_shift4.rc
[ "$rc" -eq 0 ] || exit "$rc"
obj/Vhead_guard_tb +FF +SHIFT4 > FF_shift4.log 2>&1
rc=$?; echo "$rc" > FF_shift4.rc
[ "$rc" -eq 0 ] || exit "$rc"
for file in TT_shift4.log FF_shift4.log; do
    [ "$(grep -c '^GUARD_FINAL .* fault1$' "$file")" -eq 5 ] || exit 91
done
echo 'WRONG_K_CONTROL_CAUGHT five guards at both TT and FF'
