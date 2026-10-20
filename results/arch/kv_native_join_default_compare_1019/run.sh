#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version | tee version.log
for family in scheduler rank coordinator; do
 top=${family}_compare
 if [ "$family" = scheduler ]; then top=scheduler_descriptor_baseline; fi
 /usr/bin/time -v "$v" --binary --timing -Wno-fatal --top-module "$top" --Mdir "obj_${family}" -j 2 "${family}_compare.sv" "${family}_candidate.sv" "${family}_baseline.sv" >"${family}_build.log" 2>&1
 if [ "$family" = scheduler ]; then
  for c in $(seq 0 25); do "obj_${family}/V${top}" +CASE="$c" >"scheduler_case${c}.log" 2>&1; grep -q "DEFAULT_SCHED_PASS outputs=70 case=$c " "scheduler_case${c}.log"; done
 else
  "obj_${family}/V${top}" >"${family}_run.log" 2>&1
  grep -q 'CODEC_DEFAULT_PASS' "${family}_run.log"
 fi
done
printf 'DEFAULT_COMPARE_ALL_PASS\n'
