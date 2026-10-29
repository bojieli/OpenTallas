#!/bin/bash
t=$1
L=$(cat /e/${t}_libs.f | tr "\n" " ")
yosys -q -l /e/${t}_eq.log -p "read_verilog -sv -DSYNTHESIS $L /e/${t}_gold.sv /e/${t}_gate.sv; hierarchy -check; proc; memory; setattr -mod -unset keep_hierarchy *; flatten; opt_clean; async2sync; equiv_make gold_bound gate_bound eq; hierarchy -top eq; equiv_simple -seq 3; equiv_induct -seq 3; equiv_status -assert" && echo "$t EQUIV PASS" || echo "$t EQUIV FAIL rc=$?"
