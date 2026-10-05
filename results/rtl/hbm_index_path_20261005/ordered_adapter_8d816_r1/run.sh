#!/bin/bash
set -u
cd /srv/opentallas/jobs-overflow/sagan-index-order-8d816bde5-r1
mkdir -p tmp
export TMPDIR="$PWD/tmp"
cd src
iverilog -g2012 -s tb_hbm_index_order_adapter -o ../gate.vvp rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/hbm_accel/index/ot_hbm_accel_index_order_adapter.sv rtl/chip/ot_coll_topk_merge.sv rtl/test/hbm_accel/tb_hbm_index_order_adapter.sv > ../compile.log 2>&1
rc=$?
printf "%s\n" "$rc" > ../compile.exit
if [ "$rc" -eq 0 ]; then
 vvp ../gate.vvp > ../runtime.log 2>&1
 rc=$?
 printf "%s\n" "$rc" > ../runtime.exit
fi
printf "%s\n" "$rc" > ../exit
exit "$rc"
