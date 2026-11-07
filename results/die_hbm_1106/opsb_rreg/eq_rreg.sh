#!/bin/bash
# eq_rreg.sh REPO OUT: default-text equivalence of the RREG edit (RREG = 0, no OT_OPSB_RREG) vs ddb087e49d for every
# ot_hgi_su_lgroup2_lf user: ot_hgi_sfu_opsa_group*, ot_hgi_sfu_opsb_group, ot_hgi_sfu_opsb_output (plain + OT_OPSB_N32).
# SRAM macros = the same stub in gold and gate (sram_stub.v); yosys equiv_make / equiv_simple / equiv_induct, PASS = equiv_status -assert.
W=$1; O=$2; mkdir -p $O; Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=$(ls $HOME/.local/opentallas-tools/yosys-0.68/*/yosys | head -1)
P=rtl/hbm_accel/cores_split/reform_1105s/opstore; U=rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
mkdir -p $O/old $O/new
for f in ot_hgi_sfu_opsa_group.sv ot_hgi_sfu_opsb_tiles.sv ot_hgi_su_lgroup2_lf.sv ot_hgi_su_lbank_n32.sv; do
  git -C $W show ${OLD:-ddb087e49d}:$P/$f > $O/old/$f; if [ -n "$SELF" ]; then cp $O/old/$f $O/new/$f; else cp $W/$P/$f $O/new/$f; fi; done
ST=$W/results/die_hbm_1106/opsb_rreg/sram_stub.v   # shared deterministic macro stub (black boxes leave free outputs)
for t in $(grep -ho "^module ot_hgi_sfu_ops[a-z0-9_]*" $O/new/ot_hgi_sfu_opsa_group.sv $O/new/ot_hgi_sfu_opsb_tiles.sv | awk '{print $2}'); do
 for D in "" "-DOT_OPSB_N32"; do
  [ -n "$D" ] && [ "$t" != ot_hgi_sfu_opsb_output ] && continue
  n=$t${D:+_n32}; S=$O/$n.ys
  { echo "read_verilog -sv -DSYNTHESIS $D -I$W/$P $O/old/*.sv $W/$U $ST"
    echo "hierarchy -top $t; proc; flatten; memory; opt -fast; opt_clean; async2sync; rename $t gold; design -stash gold"
    echo "read_verilog -sv -DSYNTHESIS $D -I$W/$P $O/new/*.sv $W/$U $ST"
    echo "hierarchy -top $t; proc; flatten; memory; opt -fast; opt_clean; async2sync; rename $t gate; design -stash gate"
    echo "design -copy-from gold -as gold gold; design -copy-from gate -as gate gate"
    echo "equiv_make gold gate eq; hierarchy -top eq; opt_clean; equiv_simple -seq 3; equiv_induct -undef -seq 3; equiv_status -assert"; } > $S
  ( timeout 3600 prlimit --as=40000000000 $Y -q -l $O/$n.log $S > /dev/null 2>&1; r=$?; echo "$n rc=$r $(grep -E 'Found [0-9]+ \$equiv|Of those|unproven' $O/$n.log | tail -2 | tr '\n' ' ')" ) &
 done; done; wait
