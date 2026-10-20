#!/bin/bash
# HKV-ASTK 2026-10-18: the expanded strip's compiler law = the RL1 law + constant shifts.  For every T in sweepA.tsv
# (config A minima), run D (RL3 stride4 distributed e-read) at LMAX+dL, EXP+dE, Z+dZ, READ(Z+1)+dZ and expect PASS;
# and at dZ-1 on Z expect the shift to be tight somewhere (reported, not required).  usage: OUT dL dE dZ
OUT=$1; dL=$2; dE=$3; dZ=$4
echo -e "T\tLMAX\tEXP\tZ\tREAD\tD_pass\tD_pass_Zminus1" > $OUT/shift_check.tsv
while read k T L _ _ _ a b c d rest; do [ "$k" = A ] || continue
  r(){ "$OUT/D/obj/Vtb" +T=$T +LMAX=$1 +EXP=$2 +Z=$3 +READ=$4 > $OUT/D/s_${T}_$3.log 2>&1; grep -q '^PASS qkd_astk_calendar' $OUT/D/s_${T}_$3.log && echo 1 || echo 0; }
  echo -e "$T\t$((a+dL))\t$((b+dE))\t$((c+dZ))\t$((d+dZ))\t$(r $((a+dL)) $((b+dE)) $((c+dZ)) $((d+dZ)))\t$(r $((a+dL)) $((b+dE)) $((c+dZ-1)) $((d+dZ-1)))" >> $OUT/shift_check.tsv
done < $OUT/sweepA.tsv
cat $OUT/shift_check.tsv
