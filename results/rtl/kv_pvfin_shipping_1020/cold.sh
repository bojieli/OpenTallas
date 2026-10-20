#!/bin/bash
set -eu
b=$PWD/src/shipping_proof/m0/obj/Vtb_qkd_pv_fin_s32
mkdir -p cold
for seed in 1 29 53; do
 "$b" +verilator+rand+reset+2 +verilator+seed+$seed +SEED=7 +N=40 >cold/s${seed}_normal.log 2>&1
 "$b" +verilator+rand+reset+2 +verilator+seed+$seed +SEED=9 +N=40 +STRETCH=1 >cold/s${seed}_stretch.log 2>&1
 grep -q '^PASS STRETCH=0 40 commands' cold/s${seed}_normal.log
 grep -q '^PASS STRETCH=1 40 commands' cold/s${seed}_stretch.log
done
echo 'SHIPPING COLD PASS 3seeds 240commands'
