#!/usr/bin/env bash
set -eu
base=$(pwd)
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vl" --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module test_out_protocol --Mdir "$base/obj_out_elastic" -o sim results/native_wbk_safe_1106/test_out_elastic.sv results/native_wbk_safe_1106/out_providers.sv results/native_wbk_safe_1106/out_elastic_native.sv > out_elastic.build.log 2>&1
"$base/obj_out_elastic/sim" > out_elastic.run.log 2>&1
