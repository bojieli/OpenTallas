#!/usr/bin/env bash
# DIE-HBM-61/CUTS 11-03: the cut parameters at their defaults (0) leave the shared programme RTL unchanged: yosys
# equivalence (equiv_make/simple/induct, SRAM black box) of the tree vs the recipe pin d34578d6f for the S leaf
# (pgcol DB 3) and the L leaf (pgcol DB 13, r5 producer). Fleet only (docker yosys, memory cap).
# usage: LP_ROOT=<repo> default_equiv.sh OUT   (gold files: OUT/gold from run_dcut_eq.sh layout, made here)
set -u; cd "${LP_ROOT:?}"; OUT=$(mkdir -p "${1:?}" && cd "$1" && pwd); s=rtl/hbm_accel/generic/adapters/static_su/programme
mkdir -p "$OUT/g"; for f in $s/ot_hbm_su_programme.sv $s/ot_hbm_su_programme_pgcol.sv; do git show d34578d6f:$f > "$OUT/g/$(basename $f)"; done
cp rtl/lib/ot_rst_relay.sv $s/ot_hbm_su_programme.sv $s/ot_hbm_su_programme_pgcol.sv "$OUT/"
SR=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v; cp $SR "$OUT/sram_bb.v"
rc=0
for db in 3 13; do
cat > "$OUT/eq_$db.ys" <<Y
read_verilog -sv -DSYNTHESIS /w/sram_bb.v
read_verilog -sv -DSYNTHESIS /w/ot_rst_relay.sv /w/g/ot_hbm_su_programme.sv /w/g/ot_hbm_su_programme_pgcol.sv
chparam -set DB $db -set CFGR $([ $db = 3 ] && echo 1 || echo 2) -set CPIN 1 -set RRLY 1 -set FADV 2 ot_hbm_su_programme_pgcol
hierarchy -top ot_hbm_su_programme_pgcol; proc; flatten; opt_clean; rename ot_hbm_su_programme_pgcol gold; design -stash gold
read_verilog -sv -DSYNTHESIS /w/sram_bb.v
read_verilog -sv -DSYNTHESIS /w/ot_rst_relay.sv /w/ot_hbm_su_programme.sv /w/ot_hbm_su_programme_pgcol.sv
chparam -set DB $db -set CFGR $([ $db = 3 ] && echo 1 || echo 2) -set CPIN 1 -set RRLY 1 -set FADV 2 ot_hbm_su_programme_pgcol
hierarchy -top ot_hbm_su_programme_pgcol; proc; flatten; opt_clean; rename ot_hbm_su_programme_pgcol gate; design -stash gate
design -copy-from gold -as gold gold; design -copy-from gate -as gate gate
equiv_make gold gate eq; hierarchy -top eq; async2sync; equiv_simple -seq 4; equiv_induct -seq 4; equiv_status -assert
Y
docker run --rm --memory=24g --memory-swap=24g -v "$OUT":/w openroad/orfs:asap7lock bash -lc \
  "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l /w/eq_$db.log /w/eq_$db.ys" > /dev/null 2>&1
if grep -q "Found 0 unproven" "$OUT/eq_$db.log"; then echo "DEFAULT_EQUIV DB=$db PASS $(grep -o 'Found [0-9]* \$equiv cells' $OUT/eq_$db.log | tail -1)"; else echo "DEFAULT_EQUIV DB=$db FAIL $(grep -i 'unproven\|error' $OUT/eq_$db.log | head -2)"; rc=1; fi
done; exit $rc
