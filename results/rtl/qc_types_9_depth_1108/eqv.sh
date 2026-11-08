#!/bin/bash
# usage: eqv.sh <gold.sv> <gate.sv> <tag>
cd /w
G=$1; R=$2; TAG=$3
cat > /w/eq_$TAG.ys <<YS
read_verilog -sv $G
chparam -set ENABLE 1 -set HEADS 1 -set SAFE 2 -set LOCAL_CTL 0 ot_qfd_su_kv_static_posted
hierarchy -top ot_qfd_su_kv_static_posted
rename ot_qfd_su_kv_static_posted gold
proc; flatten; opt_clean; async2sync; opt -fast
design -stash gold
read_verilog -sv $R
chparam -set ENABLE 1 -set HEADS 1 -set SAFE 2 -set LOCAL_CTL 0 -set SEAT_HT 1 ot_qfd_su_kv_static_posted
hierarchy -top ot_qfd_su_kv_static_posted
rename ot_qfd_su_kv_static_posted gate
proc; flatten; opt_clean; async2sync; opt -fast
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
YS
Y=$(ls /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys 2>/dev/null || which yosys)
$Y -q -l /w/eq_$TAG.log /w/eq_$TAG.ys; echo "RC=$?" >> /w/eq_$TAG.log
