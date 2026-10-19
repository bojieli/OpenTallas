#!/bin/bash
set -euo pipefail
for mode in r7w ovl; do
  iverilog -g2012 -s tb -o ${mode}_kept.sim functional_cells_udp.v sram.v ${mode}_mapped.v ${mode}_reset24_kept.v tb_${mode}_kept.sv > ${mode}_kept.compile.log 2>&1
  vvp ${mode}_kept.sim > ${mode}_kept.miter.log 2>&1
done
