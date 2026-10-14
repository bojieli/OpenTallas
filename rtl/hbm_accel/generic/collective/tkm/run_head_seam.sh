#!/bin/bash
set -eu
cd "$(dirname "$0")/../../../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_hgi_coll_tkm_head_seam -Ptb_hgi_coll_tkm_head_seam.MUT="${2:-0}" -Ptb_hgi_coll_tkm_head_seam.MASKED="${3:-1}" -Ptb_hgi_coll_tkm_head_seam.BLOCKS="${4:-300}" -o "$out/sim" rtl/hbm_accel/generic/collective/tkm/tb_hgi_coll_tkm_head_seam.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_seq_lane_core.sv rtl/lib/ot_rst_relay.sv
vvp "$out/sim"
