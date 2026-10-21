#!/bin/bash
# QW-CALR 10-20: CTLM successor (PRIVATE_CALR=1, F16WTN=1, wtn = closed hard child) landed lockstep on Verilator 5.050.
set -uo pipefail
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version
$V --binary --timing -j 8 -Wno-fatal --top-module tb_qfd_tt_ctlm_dv_lpf_lp -f bench9.f --Mdir ../bench9_obj > ../bench9_build.log 2>&1 || { tail -30 ../bench9_build.log; echo BENCH9_BUILD_FAIL; exit 3; }
X=../bench9_obj/Vtb_qfd_tt_ctlm_dv_lpf_lp; rc=0
chk() { local name=$1 want=$2; shift 2; $X "$@" > ../bench9_$name.out 2>&1; tail -4 ../bench9_$name.out
  if grep -q "LP_LOCKSTEP $want" ../bench9_$name.out; then echo "CASE $name expect $want OK"; else echo "CASE $name expect $want BAD"; rc=1; fi; }
chk rnd_mut0 PASS +MUT=0 +SEED=73521
chk rnd_mut1 FAIL +MUT=1 +SEED=73521
chk rnd_mut2 FAIL +MUT=2 +SEED=73521
chk calr_mut0 PASS +MUT=0 +SEED=91 +CALRDIR=1 +CALR_ROM_DIR=calr
chk calr_mut2 FAIL +MUT=2 +SEED=91 +CALRDIR=1 +CALR_ROM_DIR=calr
chk calr_rommut FAIL +MUT=0 +SEED=91 +CALRDIR=1 +CALR_ROM_DIR=calr +CALR_ROM_MUT=1
n=$(grep -c CALR_ROM_LOAD ../bench9_calr_mut0.out); echo "CALR_ROM_LOADS $n"; [ "$n" = 4 ] || rc=1
grep CALRDIR_SUMMARY ../bench9_calr_mut0.out
echo "BENCH9_RC $rc"; exit $rc
