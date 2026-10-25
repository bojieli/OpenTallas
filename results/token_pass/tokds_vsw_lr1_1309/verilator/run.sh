#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --binary --timing -j 8 -Wno-fatal -DSYNTHESIS_OFF --top-module tb_s81sl_vsw_lr_eq --Mdir obj_real tb.sv sram.v kit/*.sv >compile.log 2>&1
for seed in 12345 7 1; do obj_real/Vtb_s81sl_vsw_lr_eq +seed=$seed +ncyc=40000 | tee real_$seed.log; grep -q 'VSW_LR_EQ PASS' real_$seed.log; done
cp -a kit mut
sed -i 's/lg <= ln_g0;/lg <= ln_u0;/' mut/ot_s81sl_vsw.sv
verilator --binary --timing -j 8 -Wno-fatal -DSYNTHESIS_OFF --top-module tb_s81sl_vsw_lr_eq --Mdir obj_mut tb.sv sram.v mut/*.sv >compile_mut.log 2>&1
obj_mut/Vtb_s81sl_vsw_lr_eq +seed=12345 +ncyc=2000 | tee mutant.log
grep -q 'VSW_LR_EQ FAIL' mutant.log
echo VSW_VERILATOR_GATE_PASS
