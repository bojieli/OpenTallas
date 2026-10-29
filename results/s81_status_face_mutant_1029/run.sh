#!/bin/bash
set -e
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --cc --exe --build -j 2 -Wno-fatal --top-module tb_landing_collect --Mdir obj landing_mut.sv tb_landing_collect.sv tb_landing_collect.cpp >build.log 2>&1
set +e
./obj/Vtb_landing_collect >mutant.log 2>&1
rc=$?
cat mutant.log
printf 'MUTANT_EXIT=%s\n' "$rc"
test "$rc" -ne 0
