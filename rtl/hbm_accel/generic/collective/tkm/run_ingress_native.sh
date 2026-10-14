#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_tkm_ingress_native -Ptb_tkm_ingress_native.MUT="${2:-0}" -o "$out/sim" rtl/hbm_accel/generic/collective/tkm/tb_tkm_ingress_native.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_lane.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv
vvp "$out/sim"
