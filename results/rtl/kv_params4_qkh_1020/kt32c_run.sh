#!/bin/bash
set -eu
D=results/rtl/kv_params4_qkh_1020
B="bash $D/kt32c_bench.sh"
$B mul 0 "$PWD/kt_m0" +n=500000
$B ktree 0 "$PWD/kt_m0" +n=200000
TAG=_rand $B ktree 0 "$PWD/kt_m0" +n=100000 +warm=256 +verilator+rand+reset+2 +seed=20261020
TAG=_rst $B ktree 0 "$PWD/kt_m0" +n=200000 +rst_every=500 +seed=905
$B ktreelk 0 "$PWD/kt_m0" +n=200000
TAG=_rst $B ktreelk 0 "$PWD/kt_m0" +n=200000 +rst_every=500 +seed=173
TAG=_rst $B mul 0 "$PWD/kt_m0" +n=300000 +rst_every=400 +seed=11
if $B ktree 1 "$PWD/kt_m1" +n=200000; then echo "MUTANT 1 NOT CAUGHT"; exit 1; fi
if $B mul 7 "$PWD/kt_m7" +n=500000; then echo "MUTANT 7 NOT CAUGHT"; exit 1; fi
if $B ktree H "$PWD/kt_mH" +n=200000; then echo "MUTANT H NOT CAUGHT"; exit 1; fi
echo "KT32C SUITE PASS"
