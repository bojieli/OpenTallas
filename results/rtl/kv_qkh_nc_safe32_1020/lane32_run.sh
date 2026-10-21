#!/bin/bash
set -eu
bash results/rtl/kv_qkh_nc_safe32_1020/lane32_bench.sh lane8 0 "$PWD/lane32_m0" +n=200000 +warm=0
TAG=_rand bash results/rtl/kv_qkh_nc_safe32_1020/lane32_bench.sh lane8 0 "$PWD/lane32_m0" +n=200000 +warm=256 +verilator+rand+reset+2 +seed=20261020
if bash results/rtl/kv_qkh_nc_safe32_1020/lane32_bench.sh lane8 3 "$PWD/lane32_m3" +n=200000 +warm=0;then echo ERROR_MUTANT_PASS;exit 1;fi
