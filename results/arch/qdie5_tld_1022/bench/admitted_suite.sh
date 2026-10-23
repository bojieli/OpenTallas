#!/bin/bash
set -eu
cd src
B=results/arch/qdie5_tld_1022/bench/run_tld_chain.sh
for shape in 0 1 2; do
 case $shape in 0) ks="0 2 4";;1) ks="6 8 10";;2) ks="5";;esac
 for k in $ks; do
  SHAPE=$shape VJOBS=1 PLUSARGS="+K0=$k" RUNTAG="_k$k" bash "$B" "../b_s${shape}_v0" 0 2 ../fx ../trace.txt
  grep -q 'TLD_CHAIN PASS' "../b_s${shape}_v0/run_k$k.log"
 done
 for rv in 3 5; do
  SHAPE=$shape VJOBS=1 PLUSARGS="+K0=$k +RUNVAR=$rv" RUNTAG="_m$rv" bash "$B" "../b_s${shape}_v0" 0 2 ../fx ../trace.txt
  grep -q 'TLD_CHAIN FAIL' "../b_s${shape}_v0/run_m$rv.log"
 done
done
for v in 1 2 4; do
 SHAPE=2 VJOBS=1 PLUSARGS="+K0=5" bash "$B" "../b_s2_v$v" "$v" 2 ../fx ../trace.txt
 grep -q 'TLD_CHAIN FAIL' "../b_s2_v$v/run.log"
done
