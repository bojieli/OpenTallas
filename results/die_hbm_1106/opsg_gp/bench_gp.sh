#!/bin/bash
# bench_gp.sh REPO OUT [OLD_COMMIT]: group tiles old (OLD text, row banks) vs new (-DOT_OPSG_GP). g0, g1, b must PASS on seeds 1-3; mutants m1..m10 must FAIL.
W=$1; O=$2; OLD=${3:-origin/main}; H=$W/results/die_hbm_1106/opsg_gp; V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
P=rtl/hbm_accel/cores_split/reform_1105s/opstore; T=$W/$P; U=$W/rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv; M=$W/physical/asap7_memory_macros_v2
R='s/\bot_hgi_sfu_opsb_(group|output)\b/old_hgi_sfu_opsb_\1/g;s/\bot_hgi_sfu_opsa_(gblock|group0|group1)\b/old_hgi_sfu_opsa_\1/g;s/\bot_hgi_su_lgroup2_lf\b/old_hgi_su_lgroup2_lf/g;s/\bot_hgi_su_lbank_n32\b/old_hgi_su_lbank_n32/g'
for f in ot_hgi_sfu_opsb_tiles.sv ot_hgi_sfu_opsa_group.sv ot_hgi_su_lgroup2_lf.sv ot_hgi_su_lbank_n32.sv; do git -C $W show $OLD:$P/$f | sed -E "$R" > $O/old_$f; done
for m in 0 1 2 3 4 5 6 7 8 9 10; do sed "s/parameter integer MUT = 0/parameter integer MUT = $m/" $T/ot_hgi_su_lgroup2_gp.sv > $O/gp$m.sv; done
SRC_OLD="$O/old_ot_hgi_sfu_opsb_tiles.sv $O/old_ot_hgi_sfu_opsa_group.sv $O/old_ot_hgi_su_lgroup2_lf.sv $O/old_ot_hgi_su_lbank_n32.sv"
MAC="$M/ot_sram_1r1w_2048x32_m8_r0c0_g32/ot_sram_1r1w_2048x32_m8_r0c0_g32.v $M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
run() { # name top(g0|g1|b) mut seed
  local n=$1 t=$2 m=$3 s=$4 D
  case $t in g0) D="-DOPSA -DTOP=ot_hgi_sfu_opsa_group0 -DOTOP=old_hgi_sfu_opsa_group0 -DGVAL=2'd0";; g1) D="-DOPSA -DTOP=ot_hgi_sfu_opsa_group1 -DOTOP=old_hgi_sfu_opsa_group1 -DGVAL=2'd1";; b) D="-DTOP=ot_hgi_sfu_opsb_group -DOTOP=old_hgi_sfu_opsb_group";; esac
  rm -rf $O/$n; $V --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -DCYC=${CYC:-40000} $D -DOT_OPSG_GP --top-module tb -Mdir $O/$n -o sim \
    $H/tb_gp.sv $SRC_OLD $T/ot_hgi_sfu_opsb_tiles.sv $T/ot_hgi_sfu_opsa_group.sv $T/ot_hgi_su_lgroup2_lf.sv $O/gp$m.sv $T/ot_hgi_su_lbank_n32.sv $U $MAC > $O/$n.b.log 2>&1 || { echo "$n BUILD FAIL"; tail -4 $O/$n.b.log; return; }
  timeout 1800 $O/$n/sim +verilator+seed+$s > $O/$n.r.log 2>&1; echo "$n rc=$? $(grep -E 'LOCKSTEP' $O/$n.r.log | head -1) $(grep -m1 -E 'MISMATCH' $O/$n.r.log)"; rm -rf $O/$n; }
if [ "${QUICK:-0}" = 1 ]; then for t in g0 g1 b; do run ${t}_s1 $t 0 1 & done; wait; exit; fi
for t in g0 g1 b; do for s in 1 2 3; do run ${t}_s$s $t 0 $s & done; done; wait
for t in g0 b; do for m in 1 2 3 4 5 6 7 8 9 10; do run ${t}_m$m $t $m 1 & done; wait; done
