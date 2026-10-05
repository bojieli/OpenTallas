#!/bin/bash
# Oneshot lockstep matrix (run from the coll dir on ot-epyc1tb): <src> <outdir>
src=$1; out=$2
cfgs=()
for s in 1 2 3; do for st in 0 10 30; do for se in 0 1; do
  cfgs+=("a_s${s}_st${st}_se${se} -GN=2 -GDEPTH=16 -GLAT=11 -GFIFO_IMPL=1 -GADD_IMPL=1 -GNCOLL=300 -GSEED=$s -GSTALL_PCT=$st -GSERIAL=$se")
  cfgs+=("b_s${s}_st${st}_se${se} -GN=4 -GDEPTH=1024 -GLAT=339 -GFIFO_IMPL=2 -GADD_IMPL=1 -GNCOLL=200 -GSEED=$s -GSTALL_PCT=$st -GSERIAL=$se")
done; done; done
for s in 1 2; do
  cfgs+=("a_slow_s$s -GN=2 -GDEPTH=16 -GLAT=11 -GBPC=32 -GFIFO_IMPL=1 -GADD_IMPL=1 -GNCOLL=300 -GSEED=$s -GSTALL_PCT=10 -GSERIAL=0")
  cfgs+=("b_slow_s$s -GN=4 -GDEPTH=1024 -GLAT=339 -GBPC=32 -GFIFO_IMPL=2 -GADD_IMPL=1 -GNCOLL=200 -GSEED=$s -GSTALL_PCT=10 -GSERIAL=0")
  cfgs+=("b_lat11_s$s -GN=4 -GDEPTH=1024 -GLAT=11 -GFIFO_IMPL=2 -GADD_IMPL=1 -GNCOLL=200 -GSEED=$s -GSTALL_PCT=20 -GSERIAL=0")
  cfgs+=("a_add0_s$s -GN=2 -GDEPTH=16 -GLAT=11 -GFIFO_IMPL=1 -GADD_IMPL=0 -GNCOLL=300 -GSEED=$s -GSTALL_PCT=0 -GSERIAL=1")
  cfgs+=("b_add0_s$s -GN=4 -GDEPTH=1024 -GLAT=339 -GFIFO_IMPL=2 -GADD_IMPL=0 -GNCOLL=200 -GSEED=$s -GSTALL_PCT=0 -GSERIAL=1")
  cfgs+=("a4_s$s -GN=4 -GDEPTH=16 -GLAT=11 -GFIFO_IMPL=1 -GADD_IMPL=1 -GNCOLL=200 -GSEED=$s -GSTALL_PCT=10 -GSERIAL=0")
done
printf '%s\n' "${cfgs[@]}" | xargs -P 24 -I{} bash -c 'set -- {}; t=$1; shift; '"$(dirname $0)"'/bench_oneshot.sh '"$src $out"' $t "$@" >/dev/null 2>&1'
grep -h -E "^RESULT|^LATENCY" $out/*/run.log
