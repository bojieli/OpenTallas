#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/native_proof"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
# SYNTHESIS removes original RTL's simulation-only zero initialization of unreset ring pointers.
/usr/bin/time -v "$V" --binary --timing -O1 -DSYNTHESIS --x-assign unique --x-initial unique -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GGAP=0 --top-module tb_s81sl_ve_native -Mdir obj_hw --build-jobs 4 $(cat ../proof_files.f) ../ve_native32_limit32.v ../cell_models/coupon/library_model_pdk.v tb_s81sl_ve_native.sv >build_hw.log 2>&1
for sd in 7 29; do
 python3 tools/s81_dv/ve_golden.py fx$sd --seed $sd >gold_hw$sd.log
 /usr/bin/time -v obj_hw/Vtb_s81sl_ve_native +dir=fx$sd +verilator+rand+reset+2 +verilator+seed+$sd >run_hw$sd.log 2>&1
 grep '^PASS NATIVE' run_hw$sd.log
done
echo HARDWARE_NATIVE_PROOF_DONE
