#!/bin/bash
set -euo pipefail
iverilog -g2012 -s tb -o ffmodels.sim functional_cells_fast.v native_seq_reference.v tb_ffmodels.sv > ffmodels.compile.log 2>&1
vvp ffmodels.sim > ffmodels.log 2>&1
for mode in r7w ovl;do
iverilog -g2012 -s tb -o ${mode}_fast.sim functional_cells_fast.v sram.v ${mode}_mapped.v ${mode}_reset24_kept.v tb_${mode}_kept.sv > ${mode}_fast.compile.log 2>&1
vvp ${mode}_fast.sim > ${mode}_fast.log 2>&1
done
