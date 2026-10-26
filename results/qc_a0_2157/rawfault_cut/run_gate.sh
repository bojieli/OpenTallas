#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
yosys -Q -p 'read_verilog cone_models.v reference_cone.v reconstructed_cone.v miter.v; hierarchy -top miter; proc; flatten; opt; sat -verify -prove ok 1 -show q' > positive_sat.log 2>&1
set +e
yosys -Q -p 'read_verilog cone_models.v reference_cone.v mutant_cone.v miter.v; hierarchy -top mutant_miter; proc; flatten; opt; sat -verify -prove ok 1 -show q' > mutant_sat.log 2>&1
rc=$?
set -e
test $rc != 0
grep -q 'proof did fail' mutant_sat.log
verilator --binary --timing --top-module tb --Mdir obj_cone -j 4 -Wno-fatal cone_models.v reference_cone.v reconstructed_cone.v mutant_cone.v tb_cone.sv > build_cone.log 2>&1
./obj_cone/Vtb > lockstep.log 2>&1
cat lockstep.log
echo FAULT_CUT_GATE_PASS
