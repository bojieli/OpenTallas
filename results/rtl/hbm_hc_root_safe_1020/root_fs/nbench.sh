#!/bin/bash
# HBM-HC7-ROOT: HC_ENG bench with the gate-cloned root (retained_r5.v -> ot_hbm_hc_root_static_nat) in lockstep.
# usage: nbench.sh NAME MUT     (MUT 21 mutates only the RTL dut -> HC_NATIVE_EQ must FAIL)
set -u
d=$(pwd); n=$1; m=$2
rm -rf $d/b_$n; mkdir -p $d/b_$n && cd $d/b_$n && tar xzf $d/src2.tgz
[ -f $d/root_nat.v ] || sed 's/\bot_hbm_hc_root_static_bfc\b/ot_hbm_hc_root_static_nat/g' $d/retained_r5.v > $d/root_nat.v
HC_NATIVE="$d/root_nat.v $d/cells.v" HC_SAFE=1 HC_TAILC=1 HC_PTFS=1 HC_BUILD_JOBS=16 bash rtl/test/run_hbm_hc_root_landed.sh $d/out_$n $m 11 11 060b060b 050a070b 060b060b 050a070b > $d/bench_$n.log 2>&1
rc=$?; echo "BENCH_RC $n rc=$rc" >> $d/bench_$n.log
cp $d/out_$n/run.log $d/run_$n.log 2>/dev/null; cp $d/out_$n/build.log $d/build_$n.log 2>/dev/null; cd $d && rm -rf $d/b_$n
exit 0
