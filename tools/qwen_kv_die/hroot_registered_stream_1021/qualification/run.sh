#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
python3 generate_fixture.py >fixture.log
read -r nd np < <(python3 -c 'import json;j=json.load(open("fixture.json"));print(j["descriptors"],j["beats"])')
verilator --version >verilator.version
verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_stream -GND="$nd" -GNP="$np" --Mdir obj tb_stream.sv qkd_host_native_engine.sv ot_hdc_ingest_fp8q.sv ot_sram_1r1w_32x128_m1.v >build.log 2>&1
./obj/Vtb_stream >sim.log 2>&1
python3 check.py
