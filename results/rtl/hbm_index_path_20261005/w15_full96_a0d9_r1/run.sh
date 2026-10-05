#!/bin/bash
set -u
source ~/.opentallas-env
cd /srv/opentallas/jobs-overflow/sagan-index-w15-full96-a0d9-r1
mkdir -p tmp
export TMPDIR="$PWD/tmp"
cd src
verilator --binary --timing --assert -Wno-fatal --top-module tb_hbm_index_w15_full96 --Mdir ../obj -j 16 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/hbm_accel/index/ot_hbm_accel_index_order_adapter.sv rtl/hbm_accel/index/ot_hbm_accel_index_w15_planemajor_formatter.sv rtl/chip/ot_coll_topk_merge.sv rtl/test/hbm_accel/tb_hbm_index_w15_full96.sv > ../compile.log 2>&1
rc=$?
printf "%s\n" "$rc" > ../compile.exit
if [ "$rc" -eq 0 ]; then
 ../obj/Vtb_hbm_index_w15_full96 > ../runtime.log 2>&1
 rc=$?
 printf "%s\n" "$rc" > ../runtime.exit
fi
printf "%s\n" "$rc" > ../exit
exit "$rc"
