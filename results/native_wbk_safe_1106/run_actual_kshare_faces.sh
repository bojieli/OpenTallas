#!/usr/bin/env bash
set -eu
base=$(pwd);p=results/native_wbk_safe_1106
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vl" --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module test_out_protocol --Mdir "$base/obj_actual_kshare" -o sim "$p/test_actual_kshare_faces.sv" "$p/out_providers.sv" "$p/out_elastic_native.sv" "$p/captured_kshare_wb_faces.sv" > actual_kshare.build.log 2>&1
"$base/obj_actual_kshare/sim" > actual_kshare.run.log 2>&1
