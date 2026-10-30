#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
receipt=results/codex_head_1030/root88
vehicle=$(mktemp /tmp/head-root88.XXXXXX.vvp)
trap 'rm -f "$vehicle"' EXIT
iverilog -g2012 -s tb -o "$vehicle" "$receipt/tb.sv" rtl/common/ot_dp_clk_landing_ca.sv rtl/common/ot_dp_clk_landing.sv rtl/common/ot_meso_fifo.sv
vvp "$vehicle"
