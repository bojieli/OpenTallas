#!/bin/bash
# eq.sh TOP PARAMS(-set k v ...) DEFINES : yosys equiv old (57b15ccf22, renamed *_old) vs new default
cd /b
TOP=$1; P=$2; D=$3
cat > eq_$4.ys <<YS
read_verilog -sv -DSYNTHESIS $D old_fifo.sv old_cdc.sv /wt/rtl/lib/ot_reset_sync.sv
read_verilog -sv -DSYNTHESIS $D /wt/rtl/lib/ot_async_fifo.sv /wt/rtl/physical/ot_fdi_phy_cdc.sv
chparam $P ${TOP}_old $TOP
hierarchy -check
proc; flatten; opt_clean; memory -nomap; memory_map; opt -fast
rename ${TOP}_old gold
rename $TOP gate
async2sync
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 3
equiv_induct -seq 3
equiv_status -assert
YS
yosys -q -l eq_$4.log eq_$4.ys > /dev/null 2>&1; echo "EQ $4 rc $? $(grep -h 'Found.*equiv\|Of those\|unproven\|Equivalence successfully' eq_$4.log | tr '\n' ' ')"
