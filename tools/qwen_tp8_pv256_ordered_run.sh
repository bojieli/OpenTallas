#!/bin/bash
set -eu
# Run only inside an admitted ot-run scratch reservation, from the staged source root.
python3 tools/qwen_tp8_pv256_ordered_vectors.py --out vectors > vectors.log
verilator --cc --exe --build -j 4 -Wno-fatal --top-module ot_qwen_tp8_pv256_ordered --Mdir obj \
    rtl/hdc/nearhbm/ot_qwen_tp8_pv256_ordered.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
    rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv \
    rtl/test/nearhbm/tb_qwen_tp8_pv256_ordered.cpp > build.log 2>&1
obj/Vot_qwen_tp8_pv256_ordered vectors none rtl-leaves.bin > positive.json
python3 tools/qwen_tp8_pv256_ordered_vectors.py --out vectors --rtl-leaves rtl-leaves.bin > rtl-proof.json
for mutant in order epoch tag data; do
    obj/Vot_qwen_tp8_pv256_ordered vectors "$mutant" "mut-$mutant.bin" > "mut-$mutant.json"
done
