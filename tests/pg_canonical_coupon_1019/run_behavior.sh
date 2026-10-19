#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p evidence_v2
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version >evidence_v2/verilator.version
sha256sum "$V" >evidence_v2/verilator.sha256
python3 make_mutants.py
for m in original or bypass reset_early reset_missing; do
 src=coupon.sv
 [ "$m" = original ] || src=mut_$m.sv
 "$V" --binary --timing --top-module tb -Wno-fatal -j 4 --Mdir obj_v2_$m "$src" tb.sv >evidence_v2/build_$m.log 2>&1
 set +e
 ./obj_v2_$m/Vtb >evidence_v2/run_$m.log 2>&1
 rc=$?
 set -e
 printf '%s\n' "$rc" >evidence_v2/run_$m.rc
 if [ "$m" = original ]; then
   [ "$rc" = 0 ]; grep -q 'PASS checks=' evidence_v2/run_$m.log
 else
   [ "$rc" != 0 ]; grep -Eq 'MISMATCH|ASYNC_RESET_FAILURE' evidence_v2/run_$m.log
 fi
done
printf 'BEHAVIOR_ALL_PASS\n'
