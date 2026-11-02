#!/bin/bash
set -euo pipefail
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_current_native_leaf --build-jobs 2 -O1 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --output-split 5000 --output-split-cfuncs 500 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0' --Mdir obj -f defines.f -f source.f tb_current_native_leaf.sv >build.log 2>&1
set +e
for gap in 8 9 10 12;do obj/Vtb_current_native_leaf +GAIN_WAIT=$gap >gap${gap}.log 2>&1;echo GAP${gap}_RC=$?;grep -E 'GAIN_COMPLETION|POST_FAULT|NATIVE_POSTNORM_RESULT' gap${gap}.log;done
