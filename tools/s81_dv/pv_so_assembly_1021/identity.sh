#!/usr/bin/env bash
set -euo pipefail
O=${1:?outdir};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_pv_identity -Mdir "$O/obj" \
 rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv tools/s81_dv/pv_so_assembly_1021/tb_pv_identity.sv > "$O/build.log" 2>&1
"$O/obj/Vtb_pv_identity" > "$O/run.log" 2>&1
grep '^IDENTITY_PASS' "$O/run.log"
