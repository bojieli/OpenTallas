#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_hfd_tkm_native_config_leaf -Ptb_hfd_tkm_native_config_leaf.MUT="${2:-0}" -o "$out/sim" rtl/hbm_accel/generic/collective/physical/tb_hfd_tkm_native_config_leaf.sv rtl/hbm_accel/generic/collective/physical/ot_hfd_tkm_native_config_leaf.sv rtl/hbm_accel/generic/collective/physical/ot_hfd_tkm_native_codec.sv rtl/lib/ot_rst_relay.sv
vvp "$out/sim"
