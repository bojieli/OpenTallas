#!/bin/bash
# DIE-HBM-97 cpfire EQ step A (yosys in openroad/orfs). Usage: run_eq.sh FILE.sv MODULE "CHPARAMS" OUTDIR WRAPPER [TESTS]
#  A1 inv   : sat -tempinduct of the OT_CMD_FIRE_EARLY invariants (FORMAL asserts in the patched core) -> must PASS
#  A1 neg   : same with OT_CMD_FIRE_EARLY_NEG (fire one edge late)                                   -> must FAIL
#  A2 bmc   : miter old (no define) vs new (define), all outputs, 48 cycles from reset                    -> must PASS
#  A2 negbmc: miter old vs NEG                                                                           -> must FAIL
F=$1; M=$2; P=$3; O=$4; W=$5; T=${6:-"inv neg bmc negbmc"}; mkdir -p $O
inv() { cat <<YS
read_verilog -sv -formal -DSYNTHESIS -DOT_CMD_FIRE_EARLY -DFORMAL $1 /eq/$(basename $F)
chparam $P $M
hierarchy -top $M
proc; flatten; opt_clean; async2sync
sat -tempinduct -prove-asserts -set-at 1 rst_n 0 -maxsteps 30 -verify
YS
}
bmc() { cat <<YS
read_verilog -sv -DSYNTHESIS /eq/$(basename $F)
delete $W
chparam $P $M
hierarchy -top $M
proc
rename $M core_old
read_verilog -sv -DSYNTHESIS -DOT_CMD_FIRE_EARLY $1 /eq/$(basename $F)
delete $W
chparam $P $M
proc
rename $M core_new
miter -equiv -flatten -make_assert -ignore_gold_x core_old core_new miter
hierarchy -top miter
flatten; opt_clean; async2sync
sat -prove-asserts -set-init-zero -set-at 1 in_rst_n 0 -seq 48 -verify
YS
}
inv "" > $O/inv.ys; inv "-DOT_CMD_FIRE_EARLY_NEG" > $O/neg.ys; bmc "" > $O/bmc.ys; bmc "-DOT_CMD_FIRE_EARLY_NEG" > $O/negbmc.ys
cp $F $O/; rm -f $O/rc.txt
for t in $T; do
  timeout 3000 docker run --rm --memory 16g -v $O:/eq openroad/orfs:latest bash -c "yosys -q -l /eq/$t.log -s /eq/$t.ys" > /dev/null 2>&1; echo "$t rc $?" | tee -a $O/rc.txt
done
