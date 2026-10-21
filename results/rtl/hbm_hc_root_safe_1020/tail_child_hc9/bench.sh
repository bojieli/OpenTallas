#!/bin/bash
# HCTAIL bench runner: bench.sh NAME MUT N PARAMS OFF GAP  (RTL child)
set -u; d=$(pwd); n=$1; mut=$2; N=$3
rm -rf $d/s_$n $d/out_$n; mkdir -p $d/s_$n && cd $d/s_$n && tar xzf $d/src.tgz
TC_PARAMS="$4" TC_OFF=$5 TC_GAP=$6 BUILD_JOBS=8 bash rtl/test/run_hbm_hc_tail_child_eq.sh $d/out_$n $mut $N 1 > $d/bench_$n.log 2>&1; echo "BENCH_RC $n rc=$?" >> $d/bench_$n.log
cp $d/out_$n/run.log $d/run_$n.log 2>/dev/null; cp $d/out_$n/build.log $d/build_$n.log 2>/dev/null; cd $d && rm -rf $d/s_$n
