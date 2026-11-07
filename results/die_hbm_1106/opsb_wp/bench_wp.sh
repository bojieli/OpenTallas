#!/bin/bash
# bench_wp.sh REPO OUT: opsb_output part 41 text (OLD commit, default ddb087e49d) vs the WP form. Runs w1 / w2 / w3
# (-DOT_OPSB_WP=1/2/3) must PASS; mutants m1..m6 (ot_hgi_su_lgroup2_wp MUT, see the file header) must FAIL for WP 1, 2, 3;
# m7 (W1 winner priority) for WP 3.
W=$1; O=$2; H=$W/results/die_hbm_1106/opsb_wp; V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
P=rtl/hbm_accel/cores_split/reform_1105s/opstore; T=$W/$P; U=$W/rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
MN=$W/physical/asap7_memory_macros_v2/ot_sram_1r1w_2048x32_m8_r0c0_g32/ot_sram_1r1w_2048x32_m8_r0c0_g32.v
R='s/\bot_hgi_sfu_opsb_(group|output)\b/old_hgi_sfu_opsb_\1/g;s/\bot_hgi_su_lgroup2_lf\b/old_hgi_su_lgroup2_lf/g;s/\bot_hgi_su_lbank_n32\b/old_hgi_su_lbank_n32/g'
for f in ot_hgi_sfu_opsb_tiles.sv ot_hgi_su_lgroup2_lf.sv ot_hgi_su_lbank_n32.sv; do git -C $W show ${OLD:-ddb087e49d}:$P/$f | sed -E "$R" > $O/old_$f; done
for m in 0 1 2 3 4 5 6 7; do sed "s/parameter integer MUT = 0/parameter integer MUT = $m/" $T/ot_hgi_su_lgroup2_wp.sv > $O/wp$m.sv; done
run() { # name WP mut
  local n=$1 w=$2 m=$3; [ $m != 0 ] && cmp -s $O/wp0.sv $O/wp$m.sv && { echo "$n NOT APPLIED"; return; }
  rm -rf $O/$n; $V --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -DCYC=${CYC:-40000} -DWPV=$w -DOT_OPSB_N32 -DOT_OPSB_WP=$w --top-module tb -Mdir $O/$n -o sim \
    $H/tb_wp.sv $O/old_ot_hgi_sfu_opsb_tiles.sv $O/old_ot_hgi_su_lgroup2_lf.sv $O/old_ot_hgi_su_lbank_n32.sv \
    $T/ot_hgi_sfu_opsb_tiles.sv $T/ot_hgi_su_lgroup2_lf.sv $O/wp$m.sv $T/ot_hgi_su_lbank_n32.sv $U $MN > $O/$n.b.log 2>&1 || { echo "$n BUILD FAIL"; tail -4 $O/$n.b.log; return; }
  timeout 1800 $O/$n/sim +verilator+seed+${SEED:-1} > $O/$n.r.log 2>&1; echo "$n rc=$? $(grep -E 'LOCKSTEP|MISMATCH' $O/$n.r.log | head -2 | tr '\n' ' ')"; }
for w in 1 2 3; do run w$w $w 0 & done; wait
for w in 1 2 3; do for m in 1 2 3 4 5 6; do run w${w}m$m $w $m & done; done; run w3m7 3 7 & wait
