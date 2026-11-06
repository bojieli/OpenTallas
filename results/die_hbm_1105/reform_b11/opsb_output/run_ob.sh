#!/bin/bash
# run_ob.sh WT OUT: opsb_output old (git OLD) vs B11 form, shifts +2; MUT0 PASS, MUT1 (lw not IREG) MUT2 (sr_v not IREG) MUT3 (lf1 lowest lane wins) FAIL
W=$1; O=$2; OLD=${OLD:-c299a5dfc1}; H=$(cd "$(dirname "$0")"; pwd); V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
T=rtl/hbm_accel/cores_split/reform_1105s/opstore
git -C $W show $OLD:$T/ot_hgi_sfu_opsb_tiles.sv | sed -E 's/\bot_hgi_sfu_opsb_(group|output)\b/old_hgi_sfu_opsb_\1/g' > $O/old.sv
U=$W/rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv; M=$W/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
cp $W/$T/ot_hgi_sfu_opsb_tiles.sv $O/new0.sv; cp $W/$T/ot_hgi_su_lgroup2_lf.sv $O/lf0.sv
sed 's/q_lw <= lw;/q_lw <= 0;/; s/\.lw(q_lw)/.lw(lw)/' $O/new0.sv > $O/new1.sv; cp $O/lf0.sv $O/lf1.sv
sed 's/q_sv <= sr_v;/q_sv <= 0;/; s/\.sr_v(q_sv)/.sr_v(sr_v)/' $O/new0.sv > $O/new2.sv; cp $O/lf0.sv $O/lf2.sv
cp $O/new0.sv $O/new3.sv; cp $H/lf1.sv $O/lf3.sv
for m in 0 1 2 3; do cmp -s $O/new0.sv $O/new$m.sv && cmp -s $O/lf0.sv $O/lf$m.sv && [ $m != 0 ] && echo "m$m NOT APPLIED"; ( d=$O/m$m; rm -rf $d; $V --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -DCYC=${CYC:-40000} --top-module tb -Mdir $d -o sim $H/tb_ob.sv $O/old.sv $O/new$m.sv $O/lf$m.sv $U $M > $d.b.log 2>&1 || { echo "m$m BUILD FAIL"; tail -3 $d.b.log; exit; }; timeout 1800 $d/sim > $d.r.log 2>&1; echo "m$m rc=$? $(grep -E 'LOCKSTEP|MISMATCH' $d.r.log | head -2 | tr '\n' ' ')" ) & done; wait
