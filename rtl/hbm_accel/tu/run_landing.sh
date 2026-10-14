#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_hcoll_landing545 -Ptb_hcoll_landing545.MUT="${2:-0}" -o "$out/sim" rtl/hbm_accel/tu/tb_hcoll_landing545.sv rtl/hbm_accel/tu/ot_hcoll_landing545.sv rtl/lib/ot_rst_relay.sv
vvp "$out/sim"
