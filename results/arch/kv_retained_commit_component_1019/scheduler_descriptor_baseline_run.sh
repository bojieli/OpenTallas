#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${VERILATOR:=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}"
sha256sum scheduler_descriptor_baseline.sv private/ot_host_if_pb2_observed_rc.sv > scheduler_descriptor_baseline_run_input_hashes.txt
"$VERILATOR" --version | tee scheduler_descriptor_baseline_run_version.log
grep -q "Verilator 5.050" scheduler_descriptor_baseline_run_version.log
"$VERILATOR" --binary --timing -Wno-fatal --top-module scheduler_descriptor_baseline --Mdir scheduler_descriptor_baseline_run_obj -j 8 scheduler_descriptor_baseline.sv private/ot_host_if_pb2_observed_rc.sv >scheduler_descriptor_baseline_run_build.log 2>&1
for c in ${CASES:-0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25}; do
  scheduler_descriptor_baseline_run_obj/Vscheduler_descriptor_baseline +CASE="$c" >"scheduler_descriptor_baseline_run_case${c}.log" 2>&1
  grep -q "SCHED_PASS case=$c" "scheduler_descriptor_baseline_run_case${c}.log"
done
