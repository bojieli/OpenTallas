#!/bin/bash
set -eu
cd "$(dirname "$0")/../../../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_hfd_tkm_native_codec -Ptb_hfd_tkm_native_codec.MUT="${2:-0}" -Ptb_hfd_tkm_native_codec.STALL="${3:-1}" -o "$out/sim" rtl/hbm_accel/generic/collective/physical/ot_hfd_tkm_native_codec.sv rtl/hbm_accel/generic/collective/physical/tb_hfd_tkm_native_codec.sv
vvp "$out/sim"
