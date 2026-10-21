#!/bin/bash
# HKV-ASTK 2026-10-18: after astk_calendar_sweep.sh (same OUT, binaries reused): minimal READ age measured from EXP
# (env SW sweep table, TS, CFGS, RS output).  (the P.V pass reads e rows before the Z start), LMAX / EXP / Z at the sweep's minima.  Writes OUT/read_sweep.tsv.
OUT=$1; SW=${SW:-$OUT/sweep.tsv}; TS=${TS:-8192 1 3000}; CFGS=${CFGS:-A B C D}; RS=${RS:-$OUT/read_sweep.tsv}
run(){ "$OUT/$1/obj/Vtb" +T=$2 +LMAX=$3 +EXP=$4 +Z=$5 +READ=$6 > "$OUT/$1/q_$2_$6.log" 2>&1; grep -q '^PASS qkd_astk_calendar' "$OUT/$1/q_$2_$6.log"; }
echo -e "cfg\tT\tEXP\tZ\tREAD_min\tREAD-EXP\tmin_pass\tminus1_fail\terlat\tlast_rsp_edge" > $RS
one(){ local k=$1 T=$2 L E Z lo hi m p=0 q=0
  read L E Z < <(awk -v k=$k -v T=$T '$1==k&&$2==T{print $7,$8,$9}' $SW)
  lo=$((E+1)); hi=$((Z+1))
  while [ $lo -lt $hi ]; do m=$(( (lo+hi)/2 )); if run $k $T $L $E $Z $m; then hi=$m; else lo=$((m+1)); fi; done
  run $k $T $L $E $Z $lo && p=1; run $k $T $L $E $Z $((lo-1)) || q=1
  echo -e "$k\t$T\t$E\t$Z\t$lo\t$((lo-E))\t$p\t$q\t$(grep -o 'erlat=[-0-9]*' $OUT/$k/q_${T}_${lo}.log | cut -d= -f2)\t$(grep -o 'edges=[0-9]*' $OUT/$k/q_${T}_${lo}.log | cut -d= -f2)" >> $RS; }
for T in $TS; do for k in $CFGS; do one $k $T & done; wait; done
cat $RS
