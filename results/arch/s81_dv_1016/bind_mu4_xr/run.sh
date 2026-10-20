#!/bin/bash
# BIND mu4 xr benches: base HB0/HB1 (2 seeds), mutant bwide HB1 (must FAIL), raw witness
cd "$(dirname "$0")/src"; O=../out; mkdir -p $O
for c in "base 1 0" "base 2 0" "base 1 1" "base 2 1" "bwide 1 1" "hops 1 1"; do set -- $c
  J=4 bash tools/s81_slice/xr_bench.sh $O/$1_s$2_hb$3 $1 $2 $3 > $O/$1_s$2_hb$3.out 2>&1; echo "$1 s$2 hb$3 rc=$?" >> $O/summary.txt &
done; wait
J=4 bash tools/s81_slice/xr_bench.sh $O/bwide_raw bwide 1 1 6000 raw > $O/bwide_raw.out 2>&1; echo "bwide raw rc=$?" >> $O/summary.txt
cat $O/summary.txt
