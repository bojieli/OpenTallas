#!/usr/bin/env bash
set -euo pipefail
O=${1:?outdir};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
bash tools/s81_dv/pv_so_assembly_1021/lint.sh "$O"
"$V" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_pv_identity -Mdir "$O/identity_obj" \
 rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv tools/s81_dv/pv_so_assembly_1021/tb_pv_identity.sv > "$O/identity_build.log" 2>&1
"$O/identity_obj/Vtb_pv_identity" > "$O/identity.log" 2>&1
grep '^IDENTITY_PASS' "$O/identity.log"
bash tools/s81_dv/pv_so_assembly_1021/run.sh "$O/transport"
