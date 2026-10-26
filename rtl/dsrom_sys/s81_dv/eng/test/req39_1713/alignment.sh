#!/bin/bash
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
set +e
"$V" --lint-only -Wno-fatal --top-module dsdv_eng_tap_c_req39 -GPCBASE=1 "$K/old_tap.sv" "$K/new_tap.sv" "$K/ot_rst_relay.sv" "$K/ot_rst_relay_bounded32.sv" > "$K/invalid_base.log" 2>&1
rc=$?
set -e
[ "$rc" != 0 ] && grep -q OT_S81ENG_REQ39_REQUIRES_ALIGNED_PCBASE "$K/invalid_base.log"
echo "REQ39 invalid unaligned PCBASE rejected as required"
