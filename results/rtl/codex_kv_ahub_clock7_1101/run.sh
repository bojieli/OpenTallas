#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 4 --top-module tb_qkd_ahub_static_dw --Mdir obj -f files.txt > build.log 2>&1
set +e
./obj/Vtb_qkd_ahub_static_dw +CKMUT=0 > run_0.log 2>&1
rc=$?
echo "NOMINAL_RC $rc" | tee summary.txt
if [ "$rc" != 0 ] || ! grep -q '^AHUB_DW PASS' run_0.log; then tail -n 8 run_0.log; exit 1; fi
for m in 1 2 3 4 5; do
 ./obj/Vtb_qkd_ahub_static_dw +CKMUT=$m > run_$m.log 2>&1
 rc=$?
 if [ "$rc" = 0 ] && grep -q '^AHUB_DW PASS' run_$m.log; then echo "MUTANT_SURVIVED $m" | tee -a summary.txt; exit 1; fi
 echo "MUTANT_CAUGHT $m rc=$rc" | tee -a summary.txt
done
echo 'AHUB_CLOCK7_GATE PASS' | tee -a summary.txt
