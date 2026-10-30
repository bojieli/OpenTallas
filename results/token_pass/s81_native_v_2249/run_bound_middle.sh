#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_bound_middle --Mdir obj_bound_middle -I. -f source_middle.f native_bound_middle_fixture.sv tb_bound_middle.sv >bound_build.log 2>&1
build_rc=$?
echo "BUILD_RC $build_rc" >>bound_status.txt
if [ "$build_rc" -ne 0 ]; then tail -n 22 bound_build.log; exit "$build_rc"; fi
obj_bound_middle/Vtb_bound_middle >bound_baseline.log 2>&1
baseline_rc=$?
echo "BASELINE_RC $baseline_rc" >>bound_status.txt
obj_bound_middle/Vtb_bound_middle +bad_payload >bound_bad_payload.log 2>&1
payload_rc=$?
obj_bound_middle/Vtb_bound_middle +bad_age >bound_bad_age.log 2>&1
age_rc=$?
echo "PAYLOAD_MUTANT_RC $payload_rc AGE_MUTANT_RC $age_rc" >>bound_status.txt
tail -n 5 bound_baseline.log
if [ "$baseline_rc" -eq 0 ] && [ "$payload_rc" -ne 0 ] && [ "$age_rc" -ne 0 ]; then
  echo 'BOUND_MIDDLE_NATIVE_GATE PASS' | tee -a bound_status.txt
else
  echo 'BOUND_MIDDLE_NATIVE_GATE FAIL' | tee -a bound_status.txt
  exit 1
fi
