#!/bin/bash
# S81-BF6 final bench round (final RTL in src_bf6 + srcc): 4 frame exes N32+SOQ (+BF_FRD_CHECK) + 2 mutant exes, router
# (vec) x 4 frames P129/P130, wo_a (vecw) x 2 frames P129/P130, mutants router + wo_a P130; die-pair txn positive + 2 mutants.
set -u
R=/srv/opentallas-scratch/claude/s81-bf6-front; cd $R/src_bf6
rm -rf $R/run $R/n160_* $R/mroh_* $R/mwsel_* $R/b_*.log $R/txn $R/txn_*.log
D="-DDSFD_BF_SOQ=1 -DDSFD_BF_SOQ_SWD=160 -DDSFD_BF_N32=1"
b() { EXTRA_DEFS="$D $5" bash $R/build_seq.sh $1 $2 $3 $4; }
b col_h9_l4_nx 5 3 n160_h9nx_e5 "-DBF_FRD_CHECK" > $R/b_n160_h9nx_e5.log 2>&1 &
b col_h10_l4 2 1 n160_h10_e2 "-DBF_FRD_CHECK" > $R/b_n160_h10_e2.log 2>&1 &
b col_h9_MX_l4 1 0 n160_h9MX_e1 "-DBF_FRD_CHECK" > $R/b_n160_h9MX_e1.log 2>&1 &
b col_h9_l4_nx 2 1 n160_h9nx_e2 "-DBF_FRD_CHECK" > $R/b_n160_h9nx_e2.log 2>&1 &
b col_h10_l4 2 1 mroh_h10_e2 "-DOT_BF6_MUT_ROH" > $R/b_mroh_h10_e2.log 2>&1 &
b col_h10_l4 2 1 mwsel_h10_e2 "-DOT_BF6_MUT_WSEL" > $R/b_mwsel_h10_e2.log 2>&1 &
( cd $R/srcc && for c in n32soq mroh mwsel mwself; do python3 tools/s81/bf6_front_n32_bench.py --case $c --work ../txn/$c > ../txn_$c.log 2>&1 & done; wait
  for c in n32soq mroh mwsel mwself; do echo "TXN $c $(tail -n1 ../txn_$c.log)"; done ) &
wait
tail -qn1 $R/b_*.log
for F in u_f_0L00 u_f_0L01 u_f_0L02 u_f_0L03; do
  bash $R/rt_seq.sh $R/vec/L0/$F $F router ffn.router n160 "129,130" &
done
for F in u_f_0L00 u_f_0L01; do bash $R/rt_seq.sh $R/vecw/L0/$F $F woa attn.wo_a n160 "129,130" & done
for M in mroh mwsel; do
  bash $R/rt_seq.sh $R/vecw/L0/u_f_0L01 u_f_0L01 woa attn.wo_a $M "130" &
  bash $R/rt_seq.sh $R/vec/L0/u_f_0L01 u_f_0L01 router ffn.router $M "130" &
done
wait
echo BF6_FINAL_DONE
