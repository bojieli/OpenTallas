#!/bin/bash
set -euo pipefail
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > verilator.version
for mode in r7w ovl;do
 "$V" --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT --top-module tb -Mdir obj_${mode}_rx -o sim functional_cells_fast.v sram.v ${mode}_mapped.v ${mode}_reset24_kept.v tb_${mode}_rx.sv > ${mode}_rx.build.log 2>&1
 ./obj_${mode}_rx/sim > ${mode}_rx.log 2>&1
done
