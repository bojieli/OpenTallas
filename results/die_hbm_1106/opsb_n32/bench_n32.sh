#!/bin/bash
# bench_n32.sh REPO OUT: opsb_output old (HEAD text) vs OT_OPSB_N32 form. MUT0 must PASS; MUT1 read address bit 0 flipped,
# MUT2 write enable (w_mask_in) dropped, MUT3 write address bits [2:0]<->[10:8] swapped, MUT4 r_ce ignored (always read) must FAIL.
W=$1; O=$2; H=$W/results/die_hbm_1106/opsb_n32; V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
P=rtl/hbm_accel/cores_split/reform_1105s/opstore; T=$W/$P; U=$W/rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
MO=$W/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
MN=$W/physical/asap7_memory_macros_v2/ot_sram_1r1w_2048x32_m8_r0c0_g32/ot_sram_1r1w_2048x32_m8_r0c0_g32.v
R='s/\bot_hgi_sfu_opsb_(group|output)\b/old_hgi_sfu_opsb_\1/g;s/\bot_hgi_su_lgroup2_lf\b/old_hgi_su_lgroup2_lf/g'
git -C $W show ${OLD:-c9c3273b7d}:$P/ot_hgi_sfu_opsb_tiles.sv | sed -E "$R" > $O/old_t.sv
git -C $W show ${OLD:-c9c3273b7d}:$P/ot_hgi_su_lgroup2_lf.sv | sed -E "$R" > $O/old_lf.sv
N=$T/ot_hgi_su_lbank_n32.sv; cp $N $O/n0.sv
sed 's/\.r_addr_in(ra)/.r_addr_in({ra[10:1], ~ra[0]})/' $N > $O/n1.sv
sed "s/\.w_mask_in(1'b1)/.w_mask_in(1'b0)/" $N > $O/n2.sv
sed 's/\.w_addr_in(wa)/.w_addr_in({wa[2:0], wa[7:3], wa[10:8]})/' $N > $O/n3.sv
sed "s/\.r_ce_in(re)/.r_ce_in(1'b1)/" $N > $O/n4.sv
for m in 0 1 2 3 4; do [ $m != 0 ] && cmp -s $O/n0.sv $O/n$m.sv && echo "m$m NOT APPLIED"; ( d=$O/m$m; rm -rf $d; $V --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -DCYC=${CYC:-40000} -DOT_OPSB_N32 --top-module tb -Mdir $d -o sim $H/tb_n32.sv $O/old_t.sv $O/old_lf.sv $T/ot_hgi_sfu_opsb_tiles.sv $T/ot_hgi_su_lgroup2_lf.sv $O/n$m.sv $U $MO $MN > $d.b.log 2>&1 || { echo "m$m BUILD FAIL"; tail -5 $d.b.log; exit; }; timeout 1800 $d/sim > $d.r.log 2>&1; echo "m$m rc=$? $(grep -E 'LOCKSTEP|MISMATCH' $d.r.log | head -2 | tr '\n' ' ')" ) & done; wait
