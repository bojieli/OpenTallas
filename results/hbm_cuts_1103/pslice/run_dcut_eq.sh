#!/usr/bin/env bash
# DIE-HBM-61/CUTS 11-03: pslice_c5 dictionary-path cut form == gold (recipe pin d34578d6f) with outputs +DK edges;
# mutants (sed on a DUT copy) must FAIL. iverilog, fleet only.   usage: LP_ROOT=<repo> run_dcut_eq.sh OUT
set -u; cd "${LP_ROOT:?}"; OUT=${1:?}; mkdir -p "$OUT/gold"; rc=0
s=rtl/hbm_accel/generic/adapters/static_su/programme; GC=${GOLD_COMMIT:-d34578d6f}
for f in rtl/lib/ot_rst_relay.sv $s/ot_hbm_su_programme.sv $s/ot_hbm_su_programme_pgcol.sv; do
  git show "$GC:$f" > "$OUT/gold/$(basename $f)" || exit 2; done
python3 - "$OUT/gold" <<'PY'
import re,sys,glob
d=sys.argv[1]; fs=sorted(glob.glob(d+'/*.sv')); txt={f:open(f).read() for f in fs}
mods=set(m for t in txt.values() for m in re.findall(r'^\s*module\s+(\w+)',t,re.M))
pat=re.compile(r'\b('+'|'.join(sorted(mods,key=len,reverse=True))+r')\b')
for f,t in txt.items(): open(f,'w').write(pat.sub(lambda m:'gold_'+m.group(1),t))
print('gold modules',len(mods))
PY
SRAM=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
# mutants: name|file|from|to
MUTS=(
 "m1|ot_hbm_su_programme.sv|assign v2k=vk[DK-1];|assign v2k=vk[0];"
 "m2|ot_hbm_su_programme.sv|assign e2k=ek[DK-1];|assign e2k=ek[0];"
 "m3|ot_hbm_su_programme.sv|.r_ce_in(ren_x[bank/OG] \&\&|.r_ce_in(ren \&\&"
 "m4|ot_hbm_su_programme_pgcol.sv|.XP(4+DK)|.XP(4)"
 "m5|ot_hbm_su_programme.sv|assign dq=dr[DRLY-1];|assign dq={dr[DRLY-1][16],d_addr[c*16+:16]};"
)
CASES=${CASES:-"k3:DRLY=1,DBREG=1,DGRP=2:PASS:- k4:DRLY=2,DBREG=1,DGRP=2:PASS:- k1:DRLY=0,DBREG=1,DGRP=0:PASS:- m1:DRLY=1,DBREG=1,DGRP=2:FAIL:m1 m2:DRLY=1,DBREG=1,DGRP=2:FAIL:m2 m3:DRLY=1,DBREG=1,DGRP=2:FAIL:m3 m4:DRLY=1,DBREG=1,DGRP=2:FAIL:m4 m5:DRLY=1,DBREG=1,DGRP=2:FAIL:m5"}
for c in $CASES; do
  IFS=: read n pr e mu <<< "$c"
  d="$OUT/dut_$n"; mkdir -p "$d"; cp $s/ot_hbm_su_programme.sv $s/ot_hbm_su_programme_pgcol.sv "$d/"
  if [ "$mu" != "-" ]; then
    for m in "${MUTS[@]}"; do IFS='|' read mn mf fr to <<< "$m"; [ "$mn" = "$mu" ] || continue
      python3 -c "import sys;p,a,b=sys.argv[1:];t=open(p).read();a=a.replace('\\\\&','&');b=b.replace('\\\\&','&');assert t.count(a)==1,(a,t.count(a));open(p,'w').write(t.replace(a,b))" "$d/$mf" "$fr" "$to" || { echo "MUTANT_APPLY_FAIL $n"; rc=1; }
    done
  fi
  p=$(echo "$pr" | sed "s/^/-Ptb_pslice_dcut./; s/,/ -Ptb_pslice_dcut./g")
  ( iverilog -g2012 -o "$d/sim" -s tb_pslice_dcut $p $OUT/gold/ot_rst_relay.sv $OUT/gold/ot_hbm_su_programme.sv \
      $OUT/gold/ot_hbm_su_programme_pgcol.sv rtl/lib/ot_rst_relay.sv $d/ot_hbm_su_programme.sv $d/ot_hbm_su_programme_pgcol.sv \
      $SRAM $s/tb_pslice_dcut.sv > "$d/build.log" 2>&1 && vvp -n "$d/sim" > "$d/run.log" 2>&1 ) &
done; wait
for c in $CASES; do
  IFS=: read n pr e mu <<< "$c"; g=$(grep -o 'DCUT_EQ [A-Z]*' "$OUT/dut_$n/run.log" 2>/dev/null | head -1)
  echo "CASE $n ($pr mut $mu) expect $e: ${g:-NO_RESULT} | $(grep -h 'DCUT_EQ ' "$OUT/dut_$n/run.log" 2>/dev/null | tail -1)"
  [ "$g" = "DCUT_EQ $e" ] || rc=1
done; echo "EQ_EXIT $rc"; exit $rc
