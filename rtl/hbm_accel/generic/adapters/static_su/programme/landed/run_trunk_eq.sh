#!/usr/bin/env bash
# DIE-HBM-57/PSLICE 11-01: trunk pslice_c5 == gold (d34578d6f) with XST/OSTG delays; mutants must FAIL. Fleet only.
# usage: LP_ROOT=<repo> run_trunk_eq.sh OUT ; GOLD_COMMIT default d34578d6f
set -u; cd "${LP_ROOT:?}"; OUT=${1:?}; mkdir -p "$OUT/gold"; rc=0
s=rtl/hbm_accel/generic/adapters/static_su/programme; GC=${GOLD_COMMIT:-d34578d6f}
for f in rtl/lib/ot_rst_relay.sv $s/ot_hbm_su_programme.sv $s/ot_hbm_su_programme_pgcol.sv; do
  git show "$GC:$f" > "$OUT/gold/$(basename $f)" || exit 2; done
python3 - "$OUT/gold" <<'PY'
import re,sys,glob,os
d=sys.argv[1]; fs=sorted(glob.glob(d+'/*.sv')); txt={f:open(f).read() for f in fs}
mods=set(m for t in txt.values() for m in re.findall(r'^\s*module\s+(\w+)',t,re.M))
pat=re.compile(r'\b('+'|'.join(sorted(mods,key=len,reverse=True))+r')\b')
for f,t in txt.items(): open(f,'w').write(pat.sub(lambda m:'gold_'+m.group(1),t))
print('gold modules',len(mods))
PY
SRAM=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
[ -f $SRAM ] || SRAM=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SRCS="$OUT/gold/ot_rst_relay.sv $OUT/gold/ot_hbm_su_programme.sv $OUT/gold/ot_hbm_su_programme_pgcol.sv \
 rtl/lib/ot_rst_relay.sv $s/ot_hbm_su_programme.sv $s/ot_hbm_su_programme_pgcol.sv $SRAM $s/tb_pslice_trunk.sv"
# name:P=V,P=V:expect
CASES=${CASES:-"a1:XST=3:PASS a2:XST=4:PASS e0:OSRC=0,EIDX=0:PASS hg1:HG=1,LFX=0:PASS x1o2:XST=1,OSTG=2,HG=10:PASS m1:TMUT=1:FAIL m2:TMUT=2:FAIL m3:TMUT=3:FAIL m4:TMUT=4:FAIL"}
for c in $CASES; do
  n=${c%%:*}; r=${c#*:}; p=$(echo "${r%:*}" | sed "s/^/-G/; s/,/ -G/g")
  ( verilator --binary -j 8 -Wno-fatal -DOT_PSLICE_TRUNK --top-module tb_pslice_trunk $p $SRCS -Mdir "$OUT/obj_$n" \
    > "$OUT/build_$n.log" 2>&1 && "$OUT/obj_$n/Vtb_pslice_trunk" > "$OUT/run_$n.log" 2>&1 ) &
done; wait
for c in $CASES; do
  n=${c%%:*}; e=${c##*:}; g=$(grep -o 'TRUNK_EQ [A-Z]*' "$OUT/run_$n.log" 2>/dev/null | head -1)
  echo "CASE $n expect $e: ${g:-NO_RESULT} | $(grep -h 'TRUNK_EQ' "$OUT/run_$n.log" 2>/dev/null | tail -1)"
  [ "$g" = "TRUNK_EQ $e" ] || rc=1
done; echo "EQ_EXIT $rc"; exit $rc
