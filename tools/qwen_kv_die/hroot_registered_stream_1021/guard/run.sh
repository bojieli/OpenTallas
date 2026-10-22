#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_guard --Mdir obj tb_guard.sv qkd_hr_ingest_cdc_shell.sv ot_link_afifo.sv ot_host_reset_bank.sv ot_sram_1r1w2c_32x546_m1_p192_mir.v >build.log 2>&1
./obj/Vtb_guard >sim.log 2>&1
grep -q SPIPE6_GUARD_PASS sim.log
