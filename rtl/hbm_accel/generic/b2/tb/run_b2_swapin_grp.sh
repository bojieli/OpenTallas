#!/bin/bash
# ot_hgi_b2_swapin group bench (tb_hgi_b2_swapin_grp): run_b2_swapin_grp.sh OUT_DIR [MUT] [extra -G...]
# PASS line: TB_HGI_B2_SWAPIN_GRP PASS ... worst dispatch -> done <cycles> (price 336, limit 369); MUT 1 2 3 must FAIL,
# MUT 4 must print TB THROUGHPUT FAIL.
set -u
O=$1; M=${2:-0}; shift; shift || true
S=$(cd "$(dirname "$0")/../../../../.." && pwd)
V=${VERILATOR:-verilator}
mkdir -p "$O" && cd "$O" || exit 2
$V --binary -j 8 --top-module tb_hgi_b2_swapin_grp -Wno-fatal -Wno-lint -Wno-style --timing -O2 -GMUT=$M "$@" \
  $S/rtl/lib/ot_rst_relay.sv $S/rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv \
  $S/rtl/hbm_accel/generic/peers/ot_hgi_dma_front.sv $S/rtl/hbm_accel/generic/b2/ot_hgi_b2_swap_disp.sv \
  $S/rtl/hbm_accel/generic/b2/ot_hgi_b2_swapin.sv \
  $S/rtl/hbm_accel/generic/b2/tb/tb_hgi_b2_swapin_grp.sv --Mdir obj -o tb > build.log 2>&1 \
  || { echo "BUILD FAIL"; grep -E "%Error" build.log | head -20; exit 2; }
./obj/tb > run.log 2>&1
grep -E '^TB' run.log | tail -14
grep -q "TB_HGI_B2_SWAPIN_GRP PASS" run.log
