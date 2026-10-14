#!/bin/bash
set -eu
python3 tools/qwen_tp8_pv256_ordered_vectors.py --out vectors > vectors.log
for pair in 0 1; do
 verilator --cc --exe --build -j 4 -Wno-fatal --top-module ot_qwen_tp8_pv256_pair -GPAIR=$pair --Mdir obj-$pair rtl/hdc/nearhbm/ot_qwen_tp8_pv256_slice.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_pair.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp rtl/test/nearhbm/tb_qwen_tp8_pv256_pair.cpp > build-$pair.log 2>&1
 for mode in steady stalls epoch order first last data restart; do obj-$pair/Vot_qwen_tp8_pv256_pair vectors "$pair" "$mode" > "p$pair-$mode.json"; for ctx in 256 257 511 513 8191; do obj-$pair/Vot_qwen_tp8_pv256_pair vectors "$pair" stalls "$ctx" > "p$pair-partial-$ctx.json"; done
 obj-$pair/Vot_qwen_tp8_pv256_pair vectors "$pair" context 8193 > "p$pair-context.json"
 done
 for ctx in 256 257 511 513 8191; do obj-$pair/Vot_qwen_tp8_pv256_pair vectors "$pair" stalls "$ctx" > "p$pair-partial-$ctx.json"; done
 obj-$pair/Vot_qwen_tp8_pv256_pair vectors "$pair" context 8193 > "p$pair-context.json"
 done
