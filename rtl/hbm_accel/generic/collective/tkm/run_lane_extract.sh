#!/bin/bash
set -eu
cd "$(dirname "$0")/../../../../.."
out=$(realpath -m "$1");mkdir -p "$out"
v=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" -GMUT_LANE="${2:-0}" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hgi_coll_tkm_lane_extract -Mdir "$out/obj" rtl/hbm_accel/generic/collective/tkm/tb_hgi_coll_tkm_lane_extract.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_lane.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_cluster.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$out/build.log" 2>&1
"$out/obj/Vtb_hgi_coll_tkm_lane_extract"
