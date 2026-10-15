#!/bin/bash
set -u
pids=()
for pipe in 0 1; do
  VM_READ_PIPE=4 VM_CAP_PIPE=2 VM_WSCATTER_PIPE=$pipe bash gate.sh "$PWD/msrc" "$PWD/out_pipe$pipe" all > "gate_pipe$pipe.log" 2>&1 &
  pids+=("$!")
done
bad=0
for pipe in 0 1; do
  if wait "${pids[$pipe]}"; then rc=0; else rc=$?; bad=1; fi
  printf '%s\n' "$rc" > "exit_pipe$pipe.txt"
  tail -15 "gate_pipe$pipe.log"
  grep -q '^SPVM_GATE PASS$' "gate_pipe$pipe.log" || bad=1
done
exit "$bad"
