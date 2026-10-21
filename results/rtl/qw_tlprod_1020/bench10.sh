#!/bin/bash
# QW-TLPROD 10-20: CTLM successor ctlm9d (CALR=1, F16WTN=1, TABLE_REL producer) landed lockstep + table-load producer on Verilator 5.050.
set -uo pipefail
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version
$V --binary --timing -j 8 -Wno-fatal --top-module tb_qfd_tt_ctlm_dv_lpf_lp -f bench10.f --Mdir ../bench10_obj > ../bench10_build.log 2>&1 || { tail -30 ../bench10_build.log; echo BENCH10_BUILD_FAIL; exit 3; }
$V --binary --timing -j 8 -Wno-fatal --top-module tb_qfd_tt_ctlm_dv_lpf_lp -GCALMUT=35 -f bench10.f --Mdir ../bench10m_obj > ../bench10m_build.log 2>&1 || { tail -30 ../bench10m_build.log; echo BENCH10M_BUILD_FAIL; exit 3; }
X=../bench10_obj/Vtb_qfd_tt_ctlm_dv_lpf_lp; XM=../bench10m_obj/Vtb_qfd_tt_ctlm_dv_lpf_lp; rc=0
chk() { local name=$1 want=$2 bin=$3; shift 3; $bin "$@" > ../bench10_$name.out 2>&1; tail -6 ../bench10_$name.out
  if grep -q "LP_LOCKSTEP $want" ../bench10_$name.out; then echo "CASE $name expect $want OK"; else echo "CASE $name expect $want BAD"; rc=1; fi; }
# regression of the ctlm9c cases (old image: no REL entry -> must be unchanged)
chk rnd_mut0 PASS $X +MUT=0 +SEED=73521
chk rnd_mut1 FAIL $X +MUT=1 +SEED=73521
chk rnd_mut2 FAIL $X +MUT=2 +SEED=73521
chk calr_mut0 PASS $X +MUT=0 +SEED=91 +CALRDIR=1 +CALR_ROM_DIR=calr
chk calr_rommut FAIL $X +MUT=0 +SEED=91 +CALRDIR=1 +CALR_ROM_DIR=calr +CALR_ROM_MUT=1
# producer: one user-0 token (stages 0..37) on the produced image
chk tok_rel PASS $X +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR=calr10
chk tok_rel_rnd PASS $X +MUT=0 +SEED=6 +CALRDIR=1 +CALR_ROM_DIR=calr10
chk tok_norel FAIL $X +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR=calr10n
chk tok_abs1 FAIL $X +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR=calr10a
chk tok_drop17 FAIL $XM +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR=calr10
for c in tok_rel tok_norel tok_abs1 tok_drop17; do echo "== $c"; grep -E "TLOAD_CHECK|TLOAD_PRODUCER|TLOAD_STAGE|TLOAD_BAD|TLOAD_LAT|CALRDIR_SUMMARY" ../bench10_$c.out | head -12; done
grep -q "TLOAD_PRODUCER PASS" ../bench10_tok_rel.out || rc=1
for c in tok_norel tok_abs1 tok_drop17; do grep -q "TLOAD_PRODUCER FAIL" ../bench10_$c.out || rc=1; done
echo "BENCH10_RC $rc"; exit $rc
