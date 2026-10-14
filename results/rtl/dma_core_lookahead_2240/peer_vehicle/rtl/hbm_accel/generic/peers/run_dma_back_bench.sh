#!/bin/bash
# ot_hgi_dma_back unit bench (tb_hgi_dma_back): run_dma_back_bench.sh OUT_DIR [MUT] [extra -G...]
# PASS line: TB_HGI_DMA_BACK PASS (MUT 0) production <cycles>; MUT 1 / 2 must print FAIL.
set -u
O=$1; M=${2:-0}; shift; shift || true
S=$(cd "$(dirname "$0")/../../../.." && pwd)
V=${VERILATOR:-verilator}
mkdir -p "$O" && cd "$O" || exit 2
$V --binary -j 8 --top-module tb_hgi_dma_back -Wno-fatal -Wno-lint -Wno-style --timing -O2 -GMUT=$M "$@" \
  $S/rtl/lib/ot_rst_relay.sv $S/rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv \
  $S/rtl/hbm_accel/generic/peers/ot_hgi_dma_back.sv $S/rtl/hbm_accel/generic/peers/tb_hgi_dma_back.sv --Mdir obj -o tb > build.log 2>&1 \
  || { echo "BUILD FAIL"; tail -20 build.log; exit 2; }
./obj/tb > run.log 2>&1
grep -E '^TB' run.log | tail -14
grep -q "TB_HGI_DMA_BACK PASS" run.log
