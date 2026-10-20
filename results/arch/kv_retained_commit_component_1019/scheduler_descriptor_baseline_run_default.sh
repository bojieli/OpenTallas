#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version | grep 'Verilator 5.050'
"$v" --binary --timing -Wno-fatal --top-module scheduler_descriptor_baseline_default --Mdir scheduler_descriptor_baseline_run_default_obj -j 8 scheduler_descriptor_baseline_default.sv private/ot_host_if_pb2_observed_rc.sv scheduler_descriptor_baseline_run_original.sv >scheduler_descriptor_baseline_run_default_build.log 2>&1
scheduler_descriptor_baseline_run_default_obj/Vscheduler_descriptor_baseline_default +CASE=0 >scheduler_descriptor_baseline_run_default.log 2>&1
grep -q 'SCHED_PASS case=0' scheduler_descriptor_baseline_run_default.log
