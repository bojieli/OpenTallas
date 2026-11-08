#!/usr/bin/env bash
# Actual dsdv_svc_att decoder; engine isolated in bench, no numeric claim.
set -euo pipefail
O=$1
mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --top-module tb_svc_h8_protocol -Mdir "$O/obj" -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH -Werror-SELRANGE -Wno-TIMESCALEMOD rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv rtl/dsrom_sys/s81_dv/svc_rs/test/tb_svc_h8_protocol.sv > "$O/build.log" 2>&1
for m in 0 1 2;do
 "$O/obj/Vtb_svc_h8_protocol" +mut=$m > "$O/run_mut$m.log" 2>&1
 grep '^H8_PROTOCOL' "$O/run_mut$m.log"
done
grep -q '^H8_PROTOCOL PASS$' "$O/run_mut0.log"
for m in 1 2;do grep -q '^H8_PROTOCOL FAIL$' "$O/run_mut$m.log";done
