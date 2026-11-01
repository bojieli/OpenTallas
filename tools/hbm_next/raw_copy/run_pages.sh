#!/bin/bash
set -euo pipefail
WT=${1:?worktree};OUT=${2:?fresh output}
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
python3 "$WT/tools/hbm_next/raw_copy/pages_probe.py" --out "$OUT"
cd "$OUT"
verilator --binary --timing -j "${OT_J:-4}" -Wno-fatal --top-module tb_pages -f sources.f --Mdir obj > build.log 2>&1
./obj/Vtb_pages > baseline.log 2>&1
grep -q 'PASS NATIVE_CW308_PAGING140' baseline.log
set +e
./obj/Vtb_pages +MUT_ACTIVE=1 > mut_active.log 2>&1
rc=$?
if [ "$rc" = 0 ] || ! grep -q NATIVE_CP_PAGE_FAULT mut_active.log; then exit 1; fi
printf 'PASS NATIVE_CP_PAGING_AND_ACTIVE_WRITE_CONTROL\n' > status
