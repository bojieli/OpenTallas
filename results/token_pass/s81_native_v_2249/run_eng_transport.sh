#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_eng_transport --Mdir obj -f source.f tb_eng_transport.sv >build.log 2>&1
build_rc=$?
echo "BUILD_RC $build_rc" >>status.txt
if [ "$build_rc" -ne 0 ]; then tail -n 22 build.log; exit "$build_rc"; fi
obj/Vtb_eng_transport >baseline.log 2>&1
baseline_rc=$?
echo "BASELINE_RC $baseline_rc" >>status.txt
obj/Vtb_eng_transport +bad_payload >bad_payload.log 2>&1
payload_rc=$?
obj/Vtb_eng_transport +bad_age >bad_age.log 2>&1
age_rc=$?
echo "PAYLOAD_MUTANT_RC $payload_rc AGE_MUTANT_RC $age_rc" >>status.txt
tail -n 5 baseline.log
if [ "$baseline_rc" -eq 0 ] && [ "$payload_rc" -ne 0 ] && [ "$age_rc" -ne 0 ]; then
  echo 'ENG_NATIVE_TRANSPORT_GATE PASS' | tee -a status.txt
else
  echo 'ENG_NATIVE_TRANSPORT_GATE FAIL' | tee -a status.txt
  exit 1
fi
