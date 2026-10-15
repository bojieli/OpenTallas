#!/bin/bash
# usage: run_topk_heap.sh <out> [extra verilator -D...]   (run from the source root)
set -u
O=$1; shift; mkdir -p $O
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x $VL ] || VL=verilator
M=physical/asap7_memory_macros
$VL --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN "$@" \
 --top-module tb_hgi_idx_topk_heap -Mdir $O/obj rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_heap.sv rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_heap_dropin.sv \
 rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_registered.sv rtl/lib/ot_rst_relay.sv \
 $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
 $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/test/hbm_generic_20261009/tb_hgi_idx_topk_heap.sv \
 -j 8 > $O/build.log 2>&1 || { tail -20 $O/build.log; echo BUILD_FAIL; exit 2; }
$O/obj/Vtb_hgi_idx_topk_heap > $O/run.log 2>&1; grep -m5 ERR $O/run.log; grep 'HGI_TOPK_HEAP' $O/run.log; grep '^CASE' $O/run.log | tail -3
grep -q 'HGI_TOPK_HEAP PASS' $O/run.log
