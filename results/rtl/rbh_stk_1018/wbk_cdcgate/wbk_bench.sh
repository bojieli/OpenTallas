#!/usr/bin/env bash
# HBM-WBK 10-18: rerun RBH-STK wbq + GEN0 wb_default benches on old (pre CDC gate) and new (gated) cutthrough; diff logs.
R=/home/ubuntu/scratch/hbm-wbk-1018
run(){ t=$1 c=$2; (cd $R/$t && JOBS=8 bash rtl/hbm_accel/loader/service_native/run_stk_quadrant_bench.sh $R/out/$t/$c $c > $R/out/$t/$c.stdout 2>&1; echo "rc=$?" >> $R/out/$t/$c.stdout); }
mkdir -p $R/out/old $R/out/new
for c in wbq_e wbq_w wbq_e_wopen wbq_mut_quad wbq_mut_span wbq_mut_premature wbq_mut_ksaddr wb_default; do
 for t in old new; do run $t $c & done
done; wait
for c in wbq_e wbq_w wbq_e_wopen wbq_mut_quad wbq_mut_span wbq_mut_premature wbq_mut_ksaddr wb_default; do
 echo "== $c new: $(grep -E 'STK_|rc=' $R/out/new/$c.stdout | tr '\n' ' ') old: $(grep -E 'STK_|rc=' $R/out/old/$c.stdout | tr '\n' ' ')"
 for f in $(cd $R/out/new/$c && find . -name '*.log' ! -name 'build-*' | sort); do
  if cmp -s <(sed "s#$R/new#R#g" $R/out/new/$c/$f) <(sed "s#$R/old#R#g" $R/out/old/$c/$f); then echo "  IDENTICAL $f"; else echo "  DIFFER $f"; fi
 done
done
