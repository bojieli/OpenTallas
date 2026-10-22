#!/bin/bash
set -eu
D=results/rtl/kv_qkh_nc_safe32_1020
bash "$D/lane32_bench.sh" add 0 "$PWD/arith32_m0" +n=300000 +warm=0
bash "$D/lane32_bench.sh" prod 0 "$PWD/arith32_m0" +warm=0
bash "$D/lane32_bench.sh" lane8 0 "$PWD/arith32_m0" +n=200000 +warm=0
TAG=_rand bash "$D/lane32_bench.sh" lane8 0 "$PWD/arith32_m0" +n=200000 +warm=256 +verilator+rand+reset+2 +seed=20261020
for m in 1 2 4;do if bash "$D/lane32_bench.sh" add "$m" "$PWD/arith32_m$m" +n=300000 +warm=0;then exit 1;fi;done
if bash "$D/lane32_bench.sh" lane8 3 "$PWD/arith32_m3" +n=200000 +warm=0;then exit 1;fi
if bash "$D/lane32_bench.sh" prod 5 "$PWD/arith32_m5" +warm=0;then exit 1;fi
