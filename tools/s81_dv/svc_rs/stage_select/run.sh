#!/usr/bin/env bash
set -euo pipefail
O=../out_stage_select;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
SRC=(rtl/hdc/v41x/ot_hdc_v41x_stagepick_n32.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv tools/s81_dv/svc_rs/stage_select/tb_stagepick.sv)
sha256sum "${SRC[@]}" > "$O/sources.sha256"
"$V" --binary --timing -j 2 -Wno-fatal --top-module tb_stagepick --Mdir "$O/obj" "${SRC[@]}" > "$O/build.log" 2>&1
"$O/obj/Vtb_stagepick" > "$O/run.log" 2>&1
cat "$O/run.log"
