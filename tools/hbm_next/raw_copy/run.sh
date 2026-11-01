#!/bin/bash
set -euo pipefail
WT=${1:?worktree};OUT=${2:?fresh output};AGE=${3:-0}
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
python3 "$WT/tools/hbm_next/raw_copy/prepare.py" --out "$OUT" --cp-transport-age "$AGE"
cd "$OUT"
verilator --binary --timing -j "${OT_J:-8}" --output-split 10000 -Wno-fatal --top-module tb_raw_copy_provider -f sources.f --Mdir "$OUT/obj" > build.log 2>&1
set +e
./obj/Vtb_raw_copy_provider > baseline.log 2>&1
rc=$?
printf 'BASELINE_RC %s\n' "$rc" > status
if [ "$rc" != 0 ]; then exit "$rc"; fi
grep -q 'PASS RAW_COPY_ROLE_SHARED_NATIVE_PHY_VM_CP_PROVIDER' baseline.log || exit 1
mutants="MUT_RAW MUT_EARLY"
if [ "$AGE" = 82 ]; then mutants=MUT_CYCLE_AGE; fi
for mutant in $mutants; do
 ./obj/Vtb_raw_copy_provider +"$mutant"=1 > "$mutant.log" 2>&1
 mrc=$?
 printf '%s_RC %s\n' "$mutant" "$mrc" >> status
 if [ "$mrc" = 0 ]; then exit 2; fi
 case "$mutant" in
  MUT_CYCLE_AGE) grep -q CP_WALL_CYCLE_AGE "$mutant.log" || exit 3;;
  MUT_RAW) grep -q RAW_STATIC_START_MISSED "$mutant.log" || exit 3;;
  MUT_EARLY) grep -q VM_PROVIDER_UNEXPECTED_FAULT "$mutant.log" || exit 3;;
 esac
done
printf 'PASS_RAW_COPY_MECHANISM\n' >> status
