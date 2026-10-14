#!/bin/bash
set -eu
python3 tools/qwen_tp8_pv256_ordered_vectors.py --out vectors > vectors-vrow.log
for pair in 0 1; do
 verilator --cc --exe --build -j 4 -Wno-fatal --top-module ot_qwen_tp8_vrow_prod_tb -GPAIR=$pair --Mdir obj-row-$pair rtl/hdc/nearhbm/ot_qwen_tp8_vrow_merge.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/test/nearhbm/ot_qwen_tp8_vrow_prod_tb.sv rtl/test/nearhbm/tb_qwen_tp8_vrow_prod.cpp > build-row-$pair.log 2>&1
 for mode in none order epoch tag data restart; do obj-row-$pair/Vot_qwen_tp8_vrow_prod_tb vectors "$pair" "$mode" > "row-p$pair-$mode.json"; done
 done
