#!/bin/bash
set -euo pipefail
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for mode in r7w ovl;do
 if [ "$mode" = r7w ];then top=qkd_d2d_static_safe24; else top=qkd_d2d_static_ovl_safe24;fi
 "$V" --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT --top-module tb -Mdir obj_${mode}_broader -o sim functional_cells_fast.v sram.v ${mode}_mapped.v ${mode}_reuse/${top}.v tb_${mode}_lifecycle.sv > ${mode}.lifecycle.build.log 2>&1
 ./obj_${mode}_broader/sim > ${mode}.lifecycle.log 2>&1
done
echo COLLECT_LIFECYCLE_PASS
