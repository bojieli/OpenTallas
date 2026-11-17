#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
yosys -Q -T -p 'read_verilog exact.v; setattr -mod -unset keep_hierarchy; prep -top miter -flatten; sat -verify -prove same 1' > exact2.log 2>&1
if yosys -Q -T -p 'read_verilog mutant.v; setattr -mod -unset keep_hierarchy; prep -top miter -flatten; sat -verify -prove same 1' > mutant2.log 2>&1; then echo MUTANT_ESCAPED;exit 1;fi
echo FAULT_MERGE_EXACT_PASS_MUTANT_CAUGHT
