#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --top-module tb -j 2 -DOT_S8_SIM -Wno-fatal -Wno-lint -Wno-style --Mdir obj_actual tb.sv coupon_actual.sv tap.sv tap_helpers.sv head.sv leaf_fo32.sv leaf_fo32_w.sv rst.sv >build_actual.log 2>&1
