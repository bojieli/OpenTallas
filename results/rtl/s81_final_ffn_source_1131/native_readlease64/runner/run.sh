#!/bin/bash
set -euo pipefail
printf 'BUILD\n' > status
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_current_native_leaf --build-jobs 2 -O1 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --output-split 5000 --output-split-cfuncs 500 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0' --Mdir obj -f defines.f -f source.f tb_current_native_leaf.sv >build.log 2>&1
printf 'RUN\n' > status
python3 run_cases.py
printf 'READ_LEASE_GATE_PASS\n' > status
