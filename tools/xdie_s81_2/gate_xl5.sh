#!/bin/bash
# S81-LINK5 task 4 (10-21): rerun of the XDIE-S81-2 min / min_err / m2 cases with the stage hop on its OWN circuit
# (tb XL5 1: s_0N pair A -> next stage rank d s_0N pair B, ot_s81sl_lep_mu_ab AB_EN 1 + 2 more lane tiles / legs / PHYs;
# TP d+2 on s_7N <-> s_7N).  cwd = staged root (stage.sh defaults: G8R2 die RTL, HF-3 lane file, origin/main lep file).
# Goldens (gen_golden.py --xl5, linear deadlines LAT 564 / PER 1.345 as g564 / mr / md, --gap 100):
#   x564 = g564 calendar + --reserve-mu-tag (WN is an MU lep: its RX clears [1077:1045])   xmr / xmd = mr / md (3 users)
# Jobs: s = MU 0 leaves + WN mu_ab (the single-user die path)   m = MU 2 leaves (MU release die) + WN mu_ab
# bash tools/xdie_s81_2/gate_xl5.sh <out> s|m
set -u; O=$1; JOB=$2; mkdir -p $O
X="bash tools/xdie_s81_2/xdie2.sh"; GD=goldens
r() { n=$1; b=$2; g=$3; shift 3; ( $X run $O $b $n $GD/$g "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt
  python3 tools/xdie_s81_2/lfix_check.py $O/$n/run.log --lfix 563 >> $O/$n.txt 2>&1; gzip -kf $O/$n/run.log ) & }
bld() { b=$1; shift; $X build $O "$@" > $O/build_$b.txt 2>&1; rc=$?; echo "EXIT $rc" >> $O/build_$b.txt; return $rc; }
case $JOB in
  s) bld bS bS mu -GXL5=1 || { touch $O/DONE_${JOB}_FAILED; exit 3; }
     r x_min bS x564; r x_min_err bS x564 +ERRP=7 ;;
  m) bld bM bM mu -GMU=2 -GXL5=1 || { touch $O/DONE_${JOB}_FAILED; exit 3; }
     r x_su bM x564; r x_mu_real bM xmr; r x_mu_dense bM xmd; r x_mu_dense_err bM xmd +ERRP=7 ;;
esac
wait; touch $O/DONE_$JOB
