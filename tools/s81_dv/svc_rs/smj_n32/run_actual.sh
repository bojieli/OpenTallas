#!/usr/bin/env bash
set -euo pipefail
O=../out_smj_actual;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
SRC=(rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_glue.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_smj_payload_n32.sv tools/s81_dv/svc_rs/smj_n32/tb_smj_actual.sv)
sha256sum "${SRC[@]}" > "$O/sources.sha256"
"$V" -Irtl/dsrom_sys/s81_dv/svc_rs --binary --timing -j 2 -Wno-fatal --top-module tb_smj --Mdir "$O/obj" "${SRC[@]}" > "$O/build.log" 2>&1
"$O/obj/Vtb_smj" > "$O/run.log" 2>&1
cat "$O/run.log"
