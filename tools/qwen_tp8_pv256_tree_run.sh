#!/bin/bash
set -eu
for pair in 0 1; do
 verilator --cc --exe --build -j 4 -Wno-fatal --top-module ot_qwen_tp8_pv256_pair_tb -GPAIR=$pair -GTREE=1 -CFLAGS '-DPV_TREE' --Mdir obj-tree-$pair rtl/hdc/nearhbm/ot_qwen_tp8_pv256_slice.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_pair.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp rtl/test/nearhbm/tb_qwen_tp8_pv256_pair.cpp rtl/test/nearhbm/ot_qwen_tp8_pv256_pair_tb.sv > build-tree-$pair.log 2>&1
 for mode in steady stalls epoch order first last data restart; do obj-tree-$pair/Vot_qwen_tp8_pv256_pair_tb vectors "$pair" "$mode" > "tree-p$pair-$mode.json"; done
 for ctx in 256 257 511 513 8191; do obj-tree-$pair/Vot_qwen_tp8_pv256_pair_tb vectors "$pair" stalls "$ctx" > "tree-p$pair-partial-$ctx.json"; done
 done
