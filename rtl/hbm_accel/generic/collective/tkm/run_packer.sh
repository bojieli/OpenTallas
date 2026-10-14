#!/bin/bash
set -eu
cd "$(dirname "$0")/../../../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_hgi_coll_tkm_packer -Ptb_hgi_coll_tkm_packer.MUT="${2:-0}" -Ptb_hgi_coll_tkm_packer.ACK_SEAM="${3:-0}" -o "$out/sim" rtl/hbm_accel/generic/collective/tkm/tb_hgi_coll_tkm_packer.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_packer.sv rtl/lib/ot_rst_relay.sv
vvp "$out/sim"
