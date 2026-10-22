#!/usr/bin/env bash
set -euo pipefail
python3 adapt.py
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_truth --Mdir obj_truth adapter.v tb_truth.sv >truth.build.log 2>&1
./obj_truth/Vtb_truth >truth.log 2>&1
