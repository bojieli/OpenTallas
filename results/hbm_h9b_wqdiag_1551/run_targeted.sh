#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/runtime"
iverilog -g2012 -s wrap -o wrap.vvp common.sv off.sv on.sv tb_wrap.sv
timeout 45 stdbuf -oL vvp wrap.vvp > wrap.log 2>&1
iverilog -g2012 -s wrap -o wrap_mut.vvp common.sv off.sv on_mut.sv tb_wrap.sv
if timeout 45 stdbuf -oL vvp wrap_mut.vvp > wrap_mut.log 2>&1; then exit 8; fi
grep -q WQDIAG_WRAP_DIFF wrap_mut.log
iverilog -g2012 -s tb -Ptb.NREQ=128 -Ptb.RELOAD=151 -o phase.vvp common.sv off.sv on.sv tb.sv
if timeout 45 stdbuf -oL vvp phase.vvp +SEED=1 > phase.log 2>&1; then exit 9; fi
grep -q WQDIAG_REFRESH_PHASE phase.log
