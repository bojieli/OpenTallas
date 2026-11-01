#!/bin/bash
set -euo pipefail
WT=${1:?worktree};OUT=${2:?fresh output}
python3 "$WT/tools/hbm_next/raw_copy/formats_probe.py" --out "$OUT" --source-ref "${3:-24de429cd}"
cd "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -j "${OT_J:-4}" -Wno-fatal --top-module tb_formats_provider -f sources.f --Mdir obj > build.log 2>&1
set +e
./obj/Vtb_formats_provider > baseline.log 2>&1
rc=$?
printf 'BASELINE_RC %s\n' "$rc" > status
[ "$rc" = 0 ] || exit "$rc"
grep -q 'PASS ALL6_FORMAT_NATIVE_VM_CP_PROVIDER' baseline.log || exit 1
for m in MUT_OFFSET MUT_FORMAT; do
 ./obj/Vtb_formats_provider +"$m"=1 > "$m.log" 2>&1
 rc=$?
 printf '%s_RC %s\n' "$m" "$rc" >> status
 if [ "$rc" = 0 ] || ! grep -q FORMAT_PAYLOAD_MISMATCH "$m.log"; then exit 2; fi
done
./obj/Vtb_formats_provider +NAN_SIGN=1 > NAN_SIGN.log 2>&1
rc=$?
printf 'NAN_SIGN_RC %s\n' "$rc" >> status
if [ "${3:-24de429cd}" = 24de429cd ]; then
 [ "$rc" != 0 ] && grep -q FORMAT_PAYLOAD_MISMATCH NAN_SIGN.log || exit 2
 printf 'PASS_FINITE_ALL6_NATIVE_VM_OPEN_E4FF_NAN_SIGN\n' >> status
else
 [ "$rc" = 0 ] && grep -q 'PASS ALL6_FORMAT_NATIVE_VM_CP_PROVIDER' NAN_SIGN.log || exit 2
 printf 'PASS_ALL256_E4_AND_ALL6_NATIVE_VM\n' >> status
fi
