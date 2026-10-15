#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
FILES=( *.sv *.v )
"$V" --binary --timing -O1 -Wno-fatal -j 8 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0' --top-module tb_s81_static_fmt1_vm_sram --Mdir obj -o tb "${FILES[@]}" > build.log 2>&1 || { tail -40 build.log; exit 2; }
./obj/tb +N=28 +MUT=0 +PLAN=plan.mem +BEATS=beats.mem > base.log 2>&1 || { cat base.log; exit 3; }
cat base.log
