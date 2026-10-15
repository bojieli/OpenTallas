#!/usr/bin/env bash
set -euo pipefail
out=/tmp/hbm-dma-wb-phy-trace-run1
mkdir -p "$out"
/usr/bin/time -v -o "$out/build.time" verilator --binary --timing -j 4 -Wno-fatal --top-module tb_dma_wb_phy_static -GMUT=0 -GWB_PIPELINE=1 -GTRACE=1 --Mdir "$out/obj" -o gate ot_hgi_dma_back_static.sv ot_hgi_b2_swap_disp_static.sv ot_hgi_b2_swap_grp_static.sv ot_hgi_b2_swap_wb_grp_static.sv ot_vms_bank_static.sv ot_hbm_svc_wb_block_cdc.sv ot_hbm_svc_wb_pipeline_cdc.sv ot_hbm_svc_phy_mux.sv ot_reset_sync.sv ot_async_fifo.sv ot_hbm_accel_cdc_fifo.sv ot_sram_1r1w_128x256_m1_r2c2.v ot_sram_1r1w_1024x256_m2_r2c2.v ot_hdc_v41x_idx_hbm.sv ot_hdc_hbm_model.sv ot_chip_v41x_hbm3e_phy.sv tb_dma_wb_phy_static.sv > "$out/build.log" 2>&1
"$out/obj/gate" > "$out/sim.log" 2>&1
cat "$out/sim.log"
