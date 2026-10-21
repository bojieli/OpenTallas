#!/bin/bash
set -euo pipefail
O=../out;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mapfile -t SRC < tools/s81_dv/seqmux_source_1021/sources.txt
sha256sum "${SRC[@]}" > "$O/sources.sha256"
"$V" --lint-only --top-module dsdv_seq_host_mux_h -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -DOT_S81_SH_S10E -DOT_S81_SH_ACKP "${SRC[@]}" > "$O/mux_h_lint.log" 2>&1
echo MUX_H_ACTUAL_CHILDREN_LINT_PASS
"$V" --binary --timing -j 4 -CFLAGS -O1 --top-module tb_cr2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -DOT_S81_SH_S10E -DOT_S81_SH_ACKP --Mdir "$O/obj" "${SRC[@]}" > "$O/cr2_build.log" 2>&1
"$O/obj/Vtb_cr2" > "$O/cr2_run.log" 2>&1
cat "$O/cr2_run.log"
