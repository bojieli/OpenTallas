#!/bin/bash
# HOLD_REAL default 0: main beat_tx vs branch beat_tx, register-matched equivalence (equiv_make/simple/induct/status -assert)
set -u; OLD=$1; NEW=$2; OUT=$3; mkdir -p $OUT; cd $OUT; Y=$HOME/.local/opentallas-tools/bin/yosys; rc=0
for pt in "r553 553 2 277 0 0" "b97 97 2 62 1 0" "h553 553 3 273 1 0" "h553m1 553 3 273 1 1" "h1104 1104 4 276 0 0" "m64 64 1 64 0 0"; do set -- $pt
cat > d_$1.ys <<Y
read_verilog -sv $OLD
chparam -set W $2 -set N $3 -set P $4 -set IDLE_ZERO $5 -set MUT $6 ot_s81hd_beat_tx
hierarchy -top ot_s81hd_beat_tx; proc; flatten; opt_clean; rename ot_s81hd_beat_tx gold; design -stash g
read_verilog -sv $NEW
chparam -set W $2 -set N $3 -set P $4 -set IDLE_ZERO $5 -set MUT $6 ot_s81hd_beat_tx
hierarchy -top ot_s81hd_beat_tx; proc; flatten; opt_clean; rename ot_s81hd_beat_tx gate; design -stash h
design -copy-from g -as gold gold
design -copy-from h -as gate gate
equiv_make gold gate eq; hierarchy -top eq; async2sync
equiv_simple -seq 2; equiv_induct; equiv_status -assert
Y
$Y -q -l d_$1.log d_$1.ys >/dev/null 2>&1; r=$?; echo "== $1 rc=$r $(grep -o 'Found [0-9]* \$equiv cells.*' d_$1.log | tail -1) $(grep -o 'Of those cells [0-9]* are proven and [0-9]* are unproven' d_$1.log | tail -1)"; [ $r = 0 ] || rc=1
done; echo "EQDEF rc=$rc"; exit $rc
