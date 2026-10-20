#!/bin/bash
set -uo pipefail
O=${1:?out};mkdir -p "$O";pids=()
for kind in bank banked;do
 for m in 0 1 2;do
  bash results/arch/s81_topk5_1020/run_${kind}.sh "$O/${kind}_m$m" "$m" > "$O/${kind}_m$m.stdout.log" 2>&1 &
  pids+=("$!")
 done
done
failed=0
for p in "${pids[@]}";do wait "$p" || failed=1;done
for kind in bank banked;do for m in 0 1 2;do test -f "$O/${kind}_m$m/run.log" && grep '^HIST_BANK' "$O/${kind}_m$m/run.log";done;done
printf 'FACE2_SUITE_RC=%s\n' "$failed"
exit "$failed"
