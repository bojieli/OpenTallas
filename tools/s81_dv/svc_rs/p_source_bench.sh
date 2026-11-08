#!/usr/bin/env bash
# Run via ot-run from the repository root; bounded actual P-source GO/two-pass check.
set -euo pipefail
O=$(realpath -m "$1")
for m in base mut; do
 python3 -I tools/s81_dv/svc_rs/p_source_cut.py "$O/$m" "$m"
 iverilog -g2012 -s tb -o "$O/$m/a.vvp" "$O/$m/producer.sv" "$O/$m/tb.sv"
 vvp "$O/$m/a.vvp" | tee "$O/$m/run.log"
done
grep -q 'P_SOURCE PASS' "$O/base/run.log"
grep -q 'P_SOURCE FAIL' "$O/mut/run.log"
