#!/bin/bash
set -eu
python3 tools/qwen_tp8_pv256_ordered_vectors.py --out vectors > vectors.log
for tree in 0 1; do
 for pair in 0 1; do
  flags=(); if [ "$tree" = 1 ]; then flags=(-CFLAGS -DPV_TREE); fi
  obj="obj-small-t${tree}-p${pair}"
  verilator --cc --exe --build -j 4 -Wno-fatal --top-module ot_qwen_tp8_pv256_pair_tb -GPAIR="$pair" -GTREE="$tree" "${flags[@]}" --Mdir "$obj" rtl/hdc/nearhbm/ot_qwen_tp8_pv256_slice.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_pair.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp rtl/test/nearhbm/tb_qwen_tp8_pv256_pair.cpp rtl/test/nearhbm/ot_qwen_tp8_pv256_pair_tb.sv > "build-t${tree}-p${pair}.log" 2>&1
  for ctx in 1 2 7 8 127 128 129 255 256 257 511 513 8191 8192; do
   for mode in steady stalls; do "$obj/Vot_qwen_tp8_pv256_pair_tb" vectors "$pair" "$mode" "$ctx" > "t${tree}-p${pair}-${mode}-${ctx}.json"; done
  done
  for mode in epoch order first last data; do
   for ctx in 129 257 8192; do "$obj/Vot_qwen_tp8_pv256_pair_tb" vectors "$pair" "$mode" "$ctx" > "t${tree}-p${pair}-${mode}-${ctx}.json"; done
  done
  for ctx in 1 129 8192; do "$obj/Vot_qwen_tp8_pv256_pair_tb" vectors "$pair" restart "$ctx" > "t${tree}-p${pair}-restart-${ctx}.json"; done
  for ctx in 0 8193; do "$obj/Vot_qwen_tp8_pv256_pair_tb" vectors "$pair" context "$ctx" > "t${tree}-p${pair}-invalid-${ctx}.json"; done
 done
done
