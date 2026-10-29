#!/bin/bash
set -uo pipefail
cd "$1"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idxq_row_clear --Mdir obj -o tb tb_idxq_row_clear.sv ot_hnx_idxq_qctl.sv ot_hnx_idxn_calendar.sv ot_rst_relay.sv ot_sram_1r1w_256x256_m2_r2c2.v > build.log 2>&1 || { tail -20 build.log; exit 2; }
./obj/tb > run.log 2>&1; grep -E "ROW |ROWCLEAR" run.log
if ./obj/tb +DMUT > mutant.log 2>&1 && grep -q ROWCLEAR_PASS mutant.log; then echo MUTANT_SURVIVED; exit 1; fi
grep ROWCLEAR_FAIL mutant.log
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -GPITCH=327 --top-module tb_idxq_row_clear --Mdir obj327 -o tb tb_idxq_row_clear.sv ot_hnx_idxq_qctl.sv ot_hnx_idxn_calendar.sv ot_rst_relay.sv ot_sram_1r1w_256x256_m2_r2c2.v > build327.log 2>&1
./obj327/tb > run327.log 2>&1; grep -E "ROWCLEAR" run327.log
