#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/native_proof"
for sd in 7 29; do
 python3 tools/s81_dv/ve_golden.py fx$sd --seed $sd >gold$sd.log
 /usr/bin/time -v obj/Vtb_s81sl_ve_native +dir=fx$sd +verilator+rand+reset+2 +verilator+seed+$sd >run$sd.log 2>&1
 grep '^PASS NATIVE' run$sd.log
done
echo DIAGNOSTIC_NATIVE_PROOF_DONE
