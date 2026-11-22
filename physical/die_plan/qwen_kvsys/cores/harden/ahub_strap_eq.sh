#!/bin/bash
# KV-AHUB-RH1 11-21 bench (11-22 PASS: tables ffddffdcffdfffdf + ffe3ffe2ffe1ffe1 proven, 108097/108097 equiv cells; wrong-tie controls fail)
# KV-AHUB-RH1 RTL-RTL sequential equivalence (yosys equiv_*) REF(table T constants) vs DUT(strap core tied to T).
# usage: run_eq.sh EQDIR KIT NAME   (inside the ORFS image; KIT = strap kit with rtl/ + config.mk)
set -uo pipefail
E=$1; K=$2; N=$3
FILES=$(grep '^export VERILOG_FILES' $K/config.mk | sed 's/^export VERILOG_FILES = //; s#/work/#'$K'/#g')
cd $E
for side in ref dut; do
  top=${side}_$N
  { echo "read_verilog -defer -sv -DSYNTHESIS -I$K/rtl $FILES $E/ref_$N.sv $E/dut_$N.sv"
    echo "hierarchy -check -top $top"
    echo "setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; proc; flatten; hierarchy -top $top; opt_clean; memory -nomap; opt_clean; stat"
    echo "rename $top gold_or_gate"
    echo "write_rtlil $E/${side}_$N.il"; } > $E/${side}_$N.ys
  yosys -q -l $E/${side}_$N.log -s $E/${side}_$N.ys || { echo "EQ $N READ_FAIL $side"; exit 2; }
done
cat > $E/eq_$N.ys <<YS
read_rtlil $E/ref_$N.il
rename gold_or_gate gold
read_rtlil $E/dut_$N.il
rename gold_or_gate gate
async2sync
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple -seq 2
equiv_struct
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status
equiv_status -assert
YS
yosys -l $E/eq_$N.log -s $E/eq_$N.ys > /dev/null 2>&1; rc=$?
grep -A3 "Found .* \$equiv cells" $E/eq_$N.log | tail -4
echo "EQ $N rc=$rc"
exit $rc
