#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/runtime"
iverilog -g2012 -s tb -Ptb.NREQ=128 -o bounded.vvp common.sv off.sv on.sv tb.sv
timeout 90 stdbuf -oL vvp -v bounded.vvp +SEED=1 > bounded.log 2>&1
iverilog -g2012 -s tb -Ptb.NREQ=128 -o bounded_mut.vvp common.sv off.sv on_mut.sv tb.sv
if timeout 90 stdbuf -oL vvp bounded_mut.vvp +SEED=1 > bounded_mut.log 2>&1; then exit 8; fi
grep -q WQDIAG_EDGE bounded_mut.log
iverilog -g2012 -s tb -Ptb.NREQ=128 -Ptb.RELOAD=151 -o bounded_phase.vvp common.sv off.sv on.sv tb.sv
if timeout 45 stdbuf -oL vvp bounded_phase.vvp +SEED=1 > bounded_phase.log 2>&1; then exit 9; fi
grep -q WQDIAG_REFRESH_PHASE bounded_phase.log
