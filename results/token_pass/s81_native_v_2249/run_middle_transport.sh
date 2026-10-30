#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_middle_transport --Mdir obj_middle -f source_middle.f tb_middle_transport.sv >middle_build.log 2>&1
build_rc=$?
echo "BUILD_RC $build_rc" >>middle_status.txt
if [ "$build_rc" -ne 0 ]; then tail -n 22 middle_build.log; exit "$build_rc"; fi
obj_middle/Vtb_middle_transport >middle_baseline.log 2>&1
baseline_rc=$?
echo "BASELINE_RC $baseline_rc" >>middle_status.txt
obj_middle/Vtb_middle_transport +bad_payload >middle_bad_payload.log 2>&1
payload_rc=$?
obj_middle/Vtb_middle_transport +bad_age >middle_bad_age.log 2>&1
age_rc=$?
echo "PAYLOAD_MUTANT_RC $payload_rc AGE_MUTANT_RC $age_rc" >>middle_status.txt
tail -n 5 middle_baseline.log
if [ "$baseline_rc" -eq 0 ] && [ "$payload_rc" -ne 0 ] && [ "$age_rc" -ne 0 ]; then
  echo 'MIDDLE_NATIVE_TRANSPORT_GATE PASS' | tee -a middle_status.txt
else
  echo 'MIDDLE_NATIVE_TRANSPORT_GATE FAIL' | tee -a middle_status.txt
  exit 1
fi
