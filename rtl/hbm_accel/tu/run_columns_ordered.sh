#!/bin/bash
set -eu
cd "$(dirname "$0")/../../.."
out=$(realpath -m "$1");vec=$(realpath -m "$2");mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DTU_NOG=12 -DTU_PFMAX=512 -DTU_PCLK_IS_CLK -DTU_SYNCPHY -GMUT_COLUMN="${3:-0}" -GNATIVE_REDUCE="${4:-0}" --top-module tb_hcoll_columns_ordered --Mdir "$out/obj" rtl/hbm_accel/tu/tb_hcoll_columns_ordered.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg_cluster.sv rtl/hbm_accel/tu/ot_hcoll_reduce_lane8.sv rtl/hbm_accel/tu/ot_hcoll_operand_column512.sv rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$out/build.log" 2>&1
"$out/obj/Vtb_hcoll_columns_ordered" +VEC="$vec" +PF=384 +RANK=19 +SEED=3 +BUDGET=377.6 +CRED=113.8 | tee "$out/run.log"
