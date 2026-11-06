#!/bin/bash
set -euo pipefail
yosys -p 'read_verilog -sv actual_cfg.sv candidate_cfg.sv miter.sv; hierarchy -top miter; proc; flatten; opt; techmap; opt; sat -verify -prove correct 1 -show-inputs -show-outputs' > proof.log 2>&1
if yosys -p 'read_verilog -sv actual_cfg.sv candidate_cfg.sv miter.sv; hierarchy -top miter; proc; flatten; opt; techmap; opt; sat -verify -prove mutant_correct 1 -show-inputs -show-outputs' > mutant.log 2>&1; then echo MUTANT_ESCAPED;exit 2;fi
echo CFGCASE_ACTUAL_D_UNIVERSAL_PASS_MUTANT_CAUGHT
