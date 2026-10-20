#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version | tee scheduler_descriptor_version.log
grep -q 'Verilator 5.050' scheduler_descriptor_version.log
sha256sum private/ot_host_if_pb2_observed_rc.sv > scheduler_descriptor_source.sha256
"$v" --binary --timing -Wno-fatal --top-module scheduler_descriptor_bench --Mdir scheduler_descriptor_obj -j 8 scheduler_descriptor_bench.sv private/ot_host_if_pb2_observed_rc.sv > scheduler_descriptor_build.log 2>&1
for c in 26 27 28 29; do
 scheduler_descriptor_obj/Vscheduler_descriptor_bench +CASE=$c > scheduler_descriptor_case$c.log 2>&1
 grep -q "DESC_PASS case=$c" scheduler_descriptor_case$c.log
done
bash scheduler_descriptor_baseline_run.sh
bash scheduler_descriptor_baseline_run_default.sh
python3 scheduler_descriptor_baseline_run_mutants.py
python3 scheduler_descriptor_baseline_run_contract.py
