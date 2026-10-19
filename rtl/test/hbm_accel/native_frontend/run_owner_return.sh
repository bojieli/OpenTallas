#!/usr/bin/env bash
set -euo pipefail
out=$1;mut=${2:-0};mkdir -p "$out"
vlt="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$vlt" --version
"$vlt" --binary --timing -j 2 -Wno-fatal --top-module tb_owner_return -GMUT="$mut" --Mdir "$out/obj" rtl/hbm_accel/loader/service_native/ot_hbm_svc_four_owner_links.sv rtl/hbm_accel/loader/service_native/ot_hbm_owner_metadata_native.sv rtl/hbm_accel/loader/service_native/ot_hbm_owner_tags_native.sv rtl/hbm_accel/loader/service_native/ot_hbm_owner_return_native.sv rtl/test/hbm_accel/native_frontend/tb_owner_return.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_owner_return"
