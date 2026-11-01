#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-norm-1101/vpair_v3
cd "$R/source"
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_vpair --build-jobs 4 -Wno-fatal -Wno-TIMESCALEMOD -Wno-PINMISSING --Mdir "$R/obj" ot_rst_relay.sv ot_s81sl_rstop.sv ot_s81sl_rstopt_xo.sv tb_vpair.sv > "$R/build.log" 2>&1
"$R/obj/Vtb_vpair" > "$R/run.log" 2>&1
grep VPAIR "$R/run.log"
grep -q VPAIR_PASS "$R/run.log"
