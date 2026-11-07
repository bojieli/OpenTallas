#!/bin/bash
# bench_rr.sh REPO OUT: opsb_output part 41 text (OLD commit) vs the RREG form. Runs: r0 (no define: default text, shift 0),
# r1 / r2 (-DOT_OPSB_RREG=1/2, shift 1/2) must PASS; mutants must FAIL: a = network select not delayed with the bank reg,
# b = sr_rv not delayed, c = bank 5 bypasses its read register, d (R 2) = network output register bypassed.
W=$1; O=$2; H=$W/results/die_hbm_1106/opsb_rreg; V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
P=rtl/hbm_accel/cores_split/reform_1105s/opstore; T=$W/$P; U=$W/rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
MN=$W/physical/asap7_memory_macros_v2/ot_sram_1r1w_2048x32_m8_r0c0_g32/ot_sram_1r1w_2048x32_m8_r0c0_g32.v
R='s/\bot_hgi_sfu_opsb_(group|output)\b/old_hgi_sfu_opsb_\1/g;s/\bot_hgi_su_lgroup2_lf\b/old_hgi_su_lgroup2_lf/g;s/\bot_hgi_su_lbank_n32\b/old_hgi_su_lbank_n32/g'
for f in ot_hgi_sfu_opsb_tiles.sv ot_hgi_su_lgroup2_lf.sv ot_hgi_su_lbank_n32.sv; do git -C $W show ${OLD:-ddb087e49d}:$P/$f | sed -E "$R" > $O/old_$f; done
L=$T/ot_hgi_su_lgroup2_lf.sv; cp $L $O/lf0.sv
sed 's/wire \[LN-1:0\] sr_m = (RREG >= 1) ? sr_s_q : sr_s;/wire [LN-1:0] sr_m = sr_s;/' $L > $O/lfa.sv
sed 's/assign sr_rv = (RREG >= 2) ? srv_r2 : (RREG == 1) ? srv_r1 : sr_rv_m;/assign sr_rv = sr_rv_m;/' $L > $O/lfb.sv
sed 's/assign m_rd\[gq\] = q;/assign m_rd[gq] = (gq == 5) ? b_rd[gq] : q;/' $L > $O/lfc.sv
sed 's/assign rd = rd_q; assign sr_d = sr_d_q;/assign rd = rd_q; assign sr_d = sr_d_m;/' $L > $O/lfd.sv
run() { # name RR lf define
  local n=$1 r=$2 lf=$3 d=$4; [ "$lf" != lf0 ] && cmp -s $O/lf0.sv $O/$lf.sv && { echo "$n NOT APPLIED"; return; }
  rm -rf $O/$n; $V --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -DCYC=${CYC:-40000} -DRR=$r -DOT_OPSB_N32 $d --top-module tb -Mdir $O/$n -o sim \
    $H/tb_rr.sv $O/old_ot_hgi_sfu_opsb_tiles.sv $O/old_ot_hgi_su_lgroup2_lf.sv $O/old_ot_hgi_su_lbank_n32.sv \
    $T/ot_hgi_sfu_opsb_tiles.sv $O/$lf.sv $T/ot_hgi_su_lbank_n32.sv $U $MN > $O/$n.b.log 2>&1 || { echo "$n BUILD FAIL"; tail -4 $O/$n.b.log; return; }
  timeout 1800 $O/$n/sim > $O/$n.r.log 2>&1; echo "$n rc=$? $(grep -E 'LOCKSTEP|MISMATCH' $O/$n.r.log | head -2 | tr '\n' ' ')"; }
run r0 0 lf0 "" & run r1 1 lf0 -DOT_OPSB_RREG=1 & run r2 2 lf0 -DOT_OPSB_RREG=2 &
run r1a 1 lfa -DOT_OPSB_RREG=1 & run r1b 1 lfb -DOT_OPSB_RREG=1 & run r1c 1 lfc -DOT_OPSB_RREG=1 &
run r2a 2 lfa -DOT_OPSB_RREG=2 & run r2b 2 lfb -DOT_OPSB_RREG=2 & run r2c 2 lfc -DOT_OPSB_RREG=2 & run r2d 2 lfd -DOT_OPSB_RREG=2 & wait
