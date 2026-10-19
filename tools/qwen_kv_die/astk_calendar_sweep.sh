#!/bin/bash
# HKV-ASTK 2026-10-18: minimal-calendar sweep of the actual strip+e-read (astk_calendar_bench.sh) for four organisations:
#   A RL1 stride16 star (the hardware the compiler's attn_calendar laws were measured on), B RL1 stride4 star (closed ctl_s),
#   C RL3 stride4 star, D RL3 stride4 distributed e-read (OT_KV_ASTK_EXPAND1).  For each T it finds, in order, the minimal
#   LMAX, EXP-LMAX, Z-EXP and READ-Z (others generous), verifies min PASS and min-1 FAIL, and writes OUT/sweep.tsv.
# usage: astk_calendar_sweep.sh OUT
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; mkdir -p "$OUT"; B=$R/tools/qwen_kv_die/astk_calendar_bench.sh
declare -A CFG=([A]="16 1 0" [B]="4 1 0" [C]="4 3 0" [D]="4 3 1")
for k in A B C D; do (bash $B $OUT/$k 0 ${CFG[$k]} -- +T=1 >/dev/null 2>&1; echo "built $k") & done; wait
for k in A B C D; do [ -x $OUT/$k/obj/Vtb ] || { tail -20 $OUT/$k/build.log; echo "FAIL build $k"; exit 1; }; done
run(){ "$OUT/$1/obj/Vtb" +T=$2 +LMAX=$3 +EXP=$4 +Z=$5 +READ=$6 > "$OUT/$1/r_$2_$3_$4_$5_$6.log" 2>&1; grep -q '^PASS qkd_astk_calendar' "$OUT/$1/r_$2_$3_$4_$5_$6.log"; }
# bsearch K T FIELD LO HI : minimal value in [LO,HI] that passes (HI must pass); uses globals L E Z RD (offsets)
bs(){ local k=$1 T=$2 f=$3 lo=$4 hi=$5 m
  while [ $lo -lt $hi ]; do m=$(( (lo+hi)/2 )); eval "$f=$m"; if run $k $T $L $((L+E)) $((L+E+ZG)) $((L+E+ZG+RD)); then hi=$m; else lo=$((m+1)); fi; done
  eval "$f=$lo"; }
echo -e "cfg\tT\tLMAX\tEXP-LMAX\tZ-EXP\tREAD-Z\tLMAX\tEXP\tZ\tREAD\tmin_pass\tminus1_fail\terlat\tedges" > $OUT/sweep.tsv
sweep(){ local k=$1 T=$2
  L=350; E=150; ZG=1600; RD=1500
  run $k $T $L $((L+E)) $((L+E+ZG)) $((L+E+ZG+RD)) || { echo -e "$k\t$T\tGENEROUS_FAIL" >> $OUT/sweep.tsv; return; }
  bs $k $T L 1 350; bs $k $T E 1 150; bs $k $T ZG 4 1600; bs $k $T RD 1 1500
  local a=$L b=$((L+E)) c=$((L+E+ZG)) d=$((L+E+ZG+RD)) p=0 q=1 lg
  run $k $T $a $b $c $d && p=1
  lg=$OUT/$k/r_${T}_${a}_${b}_${c}_${d}.log
  for v in "$((a-1)) $((b-1)) $((c-1)) $((d-1))" "$a $((b-1)) $((c-1)) $((d-1))" "$a $b $((c-1)) $((d-1))" "$a $b $c $((d-1))"; do
    run $k $T $v && q=0; done
  echo -e "$k\t$T\t$L\t$E\t$ZG\t$RD\t$a\t$b\t$c\t$d\t$p\t$q\t$(grep -o 'erlat=[-0-9]*' $lg | cut -d= -f2)\t$(grep -o 'edges=[0-9]*' $lg | cut -d= -f2)" >> $OUT/sweep.tsv; }
for T in 8192 1 3000; do for k in A B C D; do sweep $k $T & done; wait; done
# mutant witnesses on D (production organisation): ep_s / ctl_s must FAIL at the generous calendar
for m in 1 3; do bash $B $OUT/Dm$m $m 4 3 1 -- +T=8192 +LMAX=350 +EXP=500 +Z=2100 +READ=3600 > $OUT/Dm$m.out 2>&1; echo "mutant $m exit $?" >> $OUT/mutants.txt; done
cat $OUT/sweep.tsv; cat $OUT/mutants.txt
