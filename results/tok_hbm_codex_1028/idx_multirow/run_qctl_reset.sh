#!/bin/bash
set -euo pipefail
cd "${1:?runtime}"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idxq_delivered_reset --Mdir objreset -o tb tb_idxq_delivered_reset.sv ot_hnx_idxq_qctl.sv ot_hnx_idxn_calendar.sv ot_rst_relay.sv ot_sram_1r1w_256x256_m2_r2c2.v > buildreset.log 2>&1
./objreset/tb > runreset.log 2>&1
grep IDXQ_RESET_PASS runreset.log
if ./objreset/tb +DROP_PRE > mutantreset.log 2>&1; then echo RESET_MUTANT_SURVIVED;exit 1;fi
grep IDXQ_RESET_FAIL mutantreset.log
