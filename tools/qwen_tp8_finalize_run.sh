#!/bin/bash
set -eu
verilator --cc --exe --build -j 4 -Wno-fatal --top-module ot_qwen_tp8_pv256_finalize_tb --Mdir obj-finalize \
 rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize.sv rtl/test/nearhbm/ot_qwen_tp8_pv256_finalize_tb.sv \
 rtl/test/nearhbm/tb_qwen_tp8_pv256_finalize.cpp rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv \
 rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp > build-finalize.log 2>&1
for mode in steady stalls data reciprocal_data epoch reciprocal_epoch restart; do
 obj-finalize/Vot_qwen_tp8_pv256_finalize_tb finalize-fixture "$mode" > "finalize-$mode.json"
done
