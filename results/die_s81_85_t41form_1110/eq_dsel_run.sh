#!/bin/bash
# T41FORM dsel equivalence: ot_meso_dsel W=64 DEPTH=4 REG=1 SPLIT=0, SREP=1 (gold, attempt_4 form) vs SREP=8 (gate).
# Sequential equivalence by induction with the 8 kept select-copy registers declared equal to the gold select register.
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
cd /eq
prep() { echo "read_verilog -sv ot_meso_fifo.sv wrap.sv; hierarchy -top $1; setattr -mod -unset keep_hierarchy *; proc; flatten; opt_clean; rename $1 $2"; }
cat > eq_dsel.ys <<YS
$(prep gold_dsel gold)
design -stash goldd
$(prep gate_dsel gate)
design -stash gated
design -copy-from goldd -as gold gold
design -copy-from gated -as gate gate
tee -o regs_gold.txt select -list gold/t:\$*dff*
tee -o regs_gate.txt select -list gate/t:\$*dff*
equiv_make gold gate equiv
hierarchy -top equiv
cd equiv
$(for r in 0 1 2 3 4 5 6 7; do echo "equiv_add -try \\u.di_gold \\u.g_srep.sr[$r].u_sel.di_gate"; done)
equiv_simple -seq 5
equiv_induct -seq 5
cd ..
equiv_status -assert
YS
$Y -s eq_dsel.ys > eq_dsel.log 2>&1; echo "rc $?"
grep -E "Found|equiv_status|proven|unproven|ERROR|Equivalence successfully" eq_dsel.log | tail -12
