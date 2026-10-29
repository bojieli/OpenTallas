#!/bin/bash
set -euo pipefail
cd "${1:?runtime}"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idxq818 --Mdir obj -o tb tb_idxq818.sv ot_hbm_static_cfg_collar.sv ot_hbm_static_cfg_collar_idxq818.sv > build.log 2>&1
./obj/tb > run.log 2>&1
grep IDX256_PASS run.log
if ./obj/tb +DROP_EXT > mutant.log 2>&1; then echo MUTANT_SURVIVED; exit 1; fi
grep 'IDX256_FAIL operand identity' mutant.log
echo IDXQ818_PASS
