#!/bin/bash
# eq.sh TAG MUT_FP  (run inside orfs container, /fv = this dir, /wt = worktree)
T=$1; MUT=$2
A=/wt/rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_argmax_static.sv
B=/wt/rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv
cat > /fv/eq_$T.ys <<EOT
read_verilog -sv $B $A /fv/wrap_gold.sv
hierarchy -top eqtop
proc; flatten; async2sync; opt_clean; rename eqtop gold; design -stash gold
read_verilog -sv $B $A /fv/wrap_gate.sv
hierarchy -top eqtop -chparam MUT_FP $MUT
proc; flatten; async2sync; opt_clean; rename eqtop gate; design -stash gate
design -copy-from gold -as gold gold; design -copy-from gate -as gate gate
equiv_make -blacklist /fv/blacklist.txt gold gate eq; hierarchy -top eq; async2sync; equiv_simple -seq 5; equiv_induct -seq 5; equiv_status -assert
EOT
Y=$(ls /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys 2>/dev/null || which yosys)
$Y -q -l /fv/eq_$T.log -p "script /fv/eq_$T.ys" > /dev/null 2>&1; echo "EQ $T rc $?"
grep -E "Found [0-9]+ .equiv|proven and|unproven|ERROR|Equivalence successfully" /fv/eq_$T.log | tail -5
