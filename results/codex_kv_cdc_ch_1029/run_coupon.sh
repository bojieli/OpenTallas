#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$(dirname "$0")"
verilator --binary --timing -Wno-fatal -j 2 --top-module tb_preserve -Mdir obj_nom tb_preserve.sv > build_nom.log 2>&1
./obj_nom/Vtb_preserve > nominal.log 2>&1
verilator --binary --timing -Wno-fatal -j 2 --top-module tb_preserve -GMUT=1 -Mdir obj_mut tb_preserve.sv > build_mut.log 2>&1
set +e
./obj_mut/Vtb_preserve > mutant.log 2>&1
rc=$?
set -e
test "$rc" != 0
grep -q 'PRESERVE mutant/mismatch' mutant.log
echo 'PASS nominal and mutant caught'
