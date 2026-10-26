#!/bin/bash
# Q-ATTN r3 serializer decision: actual ME controller/port (Codex extraction, tools/qwen_producer_train/component_sources.sv)
# runs every result-producing decoder ME instruction of the shipped decoder programme; captures replayed into
# (a) qfd_res_train_static and (b) qfd_res_ser_static (raw actual timing, and a hypothetical 24-spaced producer).
set -euo pipefail
R=$(git rev-parse --show-toplevel); D=$(cd "$(dirname "$0")" && pwd); O=${OUT:-/tmp/res_train_decision}
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_sertrade --Mdir "$O" \
  "$D/tb_sertrade.sv" "$R/tools/qwen_producer_train/component_sources.sv" "$R/rtl/qwen_split/qfd_res_train_static.sv" -j 16 > "$O.build.log" 2>&1
while read -r pc args; do echo "$pc $("$O/Vtb_sertrade" $args 2>&1 | grep -E '^\{')"; done < "$D/pcs.txt"
