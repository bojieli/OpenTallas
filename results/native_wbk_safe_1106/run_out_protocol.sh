#!/usr/bin/env bash
set -eu
base=$(pwd)
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vl" --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module test_out_protocol --Mdir "$base/obj_out_protocol" -o sim results/native_wbk_safe_1106/test_out_protocol.sv results/native_wbk_safe_1106/out_providers.sv > out_protocol.build.log 2>&1
"$base/obj_out_protocol/sim" > out_protocol.run.log 2>&1
