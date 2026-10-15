#!/usr/bin/env bash
# Four independent fullshape native gates share a compiled source-pinned binary.
# Runtime budget8GiB/4threads: measured predecessor480MB RSS per binary.
set -euo pipefail
bin=$(realpath "$1")
vectors=$(realpath "$2")
out=$(realpath -m "$3")
mkdir -p "$out"
sha256sum "$bin" "$vectors/seed.mem" "$vectors/control.mem" "$vectors/gold.mem" > "$out/sha256.txt"
declare -a jobs
for mode in base ADDR PHASE DATA;do
 args=()
 if [ "$mode" != base ];then args+=(+MUT_"$mode");fi
 /usr/bin/time -v -o "$out/$mode.time" "$bin" +DIR="$vectors" "${args[@]}" > "$out/$mode.log" 2>&1 &
 jobs+=("$!")
done
error=0
index=0
for mode in base ADDR PHASE DATA;do
 set +e
 wait "${jobs[$index]}"
 rc=$?
 set -e
 printf '%s\n' "$rc" > "$out/$mode.exit"
 if [ "$mode" = base ];then
  if [ "$rc" != 0 ] || ! grep -q 'SU_ARITH PASS' "$out/$mode.log";then error=1;fi
 else
  if [ "$rc" = 0 ] || ! grep -q 'SU_ARITH FAIL' "$out/$mode.log";then error=1;fi
 fi
 index=$((index+1))
done
if [ "$error" != 0 ];then echo 'SU_ARITH SUITE FAIL';exit 1;fi
cat "$out/base.log"
echo 'SU_ARITH SUITE PASS actualfullshape base and3failingmutants'
