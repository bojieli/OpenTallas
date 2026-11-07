#!/bin/bash
# eqoff.sh MODULE GOLDFILE GATEFILE [chparams for both]
M=$1; G=$2; N=$3; shift 3; CP="$*"
cat > /tmp/eq_$M.ys <<EOT
read_verilog -sv /fv/bb.v
read_verilog -sv $G
$( [ -n "$EXTRA" ] && echo "read_verilog -sv $EXTRA" )
hierarchy -top $M $CP
proc; flatten; async2sync; opt_clean; rename $M gold; design -stash gold
read_verilog -sv /fv/bb.v
read_verilog -sv $N
$( [ -n "$EXTRA" ] && echo "read_verilog -sv $EXTRA" )
hierarchy -top $M $CP
proc; flatten; async2sync; opt_clean; rename $M gate; design -stash gate
design -copy-from gold -as gold gold; design -copy-from gate -as gate gate
equiv_make gold gate eq; hierarchy -top eq; async2sync; equiv_simple -seq 5; equiv_induct -seq 5; equiv_status -assert
EOT
yosys -p "script /tmp/eq_$M.ys" > /fv/eq_$M.log 2>&1; echo "EQOFF $M rc $?"
