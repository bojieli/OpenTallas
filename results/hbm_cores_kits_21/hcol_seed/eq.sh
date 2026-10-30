#!/bin/bash
# HBM-CORES-KITS-21 hcol seed proof (yosys sat in openroad/orfs:asap7lock, run in docker --memory=16g).
# A1: old == new on csi_p, cs_o, cf_o every edge from a zero power-up (BMC 30 + k-induction)
# A2: old == new on every edge >= 9 from an ARBITRARY (undef) power-up: the old 9-edge X chain (7-stage line + cs_o + csi_p) is the only difference
# B : new csi_p[15:0] = cs_o[15:0] = 0 on every edge >= 2 from an arbitrary power-up (BMC 12)
# N1 (N1b): old vs new from an arbitrary power-up compared from edge 0 (edge 8) must FAIL (the power-up window is real)
# N2: old vs mutant (zero-mantissa flush dropped) must FAIL from zero power-up
cd /c; O=/c/out; mkdir -p $O; D=/c/ot_hdc_delay.sv  # copy rtl/hdc/ot_hdc_delay.sv into the run dir
run() { # name A B satargs
sed "s/miter_A_B/miter_$2_$3/; s/seed_A/seed_$2/; s/seed_B/seed_$3/" seed.v > $O/s_$1.v
cat > $O/$1.ys <<YS
read_verilog -sv $D $O/s_$1.v
hierarchy -top miter_$2_$3
proc; flatten; opt_clean
sat -verify $4 -set-def-inputs -prove trigger 0 miter_$2_$3
YS
if timeout 1800 yosys -q -s $O/$1.ys > $O/$1.log 2>&1; then echo "$1: PASS"; else echo "$1: FAIL (rc=$?)"; fi
}
run A1_bmc30 old new "-seq 30 -set-init-zero"
run A1_induct old new "-tempinduct -maxsteps 20 -set-init-zero"
run A2_arbinit_from_edge9 old new "-seq 40 -prove-skip 9 -set-init-undef"
run N1b_arbinit_from_edge8 old new "-seq 40 -prove-skip 8 -set-init-undef"
run N1_arbinit_from1 old new "-seq 9 -set-init-undef"
run N2_mutant old mut "-seq 12 -set-init-zero"
cat > $O/B.ys <<YS
read_verilog -sv $D seed.v
hierarchy -top lowchk
proc; flatten; opt_clean
sat -verify -seq 12 -prove-skip 2 -set-init-undef -set-def-inputs -prove bad 0 lowchk
YS
if timeout 600 yosys -q -s $O/B.ys > $O/B.log 2>&1; then echo "B_low16_zero_from2: PASS"; else echo "B_low16_zero_from2: FAIL"; fi
echo DONE
