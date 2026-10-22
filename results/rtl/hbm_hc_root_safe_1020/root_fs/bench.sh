#!/bin/bash
# usage: bench.sh NAME MUT SAFE TAILC   (landed d4g smoke params of hbm_hc_root_d4g_xr2)
set -u
d=$(pwd); n=$1; m=$2; sf=$3; tc=$4; pf=${5:-0}
rm -rf $d/b_$n; mkdir -p $d/b_$n && cd $d/b_$n && tar xzf $d/src.tgz
HC_SAFE=$sf HC_TAILC=$tc HC_PTFS=$pf HC_BUILD_JOBS=16 bash rtl/test/run_hbm_hc_root_landed.sh $d/out_$n $m 11 11 060b060b 050a070b 060b060b 050a070b > $d/bench_$n.log 2>&1
rc=$?; echo "BENCH_RC $n rc=$rc" >> $d/bench_$n.log
cp $d/out_$n/run.log $d/run_$n.log 2>/dev/null; cd $d && rm -rf $d/b_$n
exit 0
