#!/bin/bash
# tb_hgi_b2_dma_q (the hardened B2 cluster DMA unit ot_hgi_b2_dma_q at production parameters; bench-own HBM / VM models):
#   run_b2_dma_q_bench.sh OUT_DIR [mut | mut2 | -G...]
# PASS line: B2_DMA_Q PASS checked=<N> ...   (mut = -GMUT_B2=1, mut2 = -GMUT_B2=2: the run must print B2_DMA_Q FAIL)
set -u
O=$1; shift
G=()
for a in "$@"; do case "$a" in mut) G+=(-GMUT_B2=1);; mut2) G+=(-GMUT_B2=2);; *) G+=("$a");; esac; done
S=$(cd "$(dirname "$0")/../../../.." && pwd)
V=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
P=$S/rtl/hbm_accel/generic/peers
mkdir -p "$O" && cd "$O" || exit 2
$V --binary -j 8 --top-module tb_hgi_b2_dma_q -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --timing -O1 "${G[@]}" \
  -y $S/rtl/lib -y $P \
  $S/rtl/lib/ot_rst_relay.sv $S/rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv \
  $S/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  $S/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v \
  $S/rtl/link/ot_fifo_sram_fwft.sv $S/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  $S/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  $S/rtl/hbm_accel/generic/adapters/ot_hgi_dma_record.sv $P/ot_hgi_dma_engines.sv $P/ot_hgi_dma_front.sv $P/ot_hgi_dma_back.sv \
  $P/ot_hgi_dma_mover.sv $P/ot_hgi_dma_mover_serial.sv $P/ot_hgi_dma_kvw.sv $P/ot_hgi_dma_mover_el.sv \
  $P/ot_hgi_b2_qrot.sv $P/ot_hgi_b2_dma_q_flat.sv $P/ot_hgi_b2_dma_q.sv $S/rtl/test/hbm_accel/b2_dma/tb_hgi_b2_dma_q.sv --Mdir obj -o tb > build.log 2>&1 \
  || { echo "BUILD FAIL"; grep -m10 -E "%Error" build.log; exit 2; }
timeout 3600 ./obj/tb ${TB_ARGS:-} > run.log 2>&1
grep -E "^(B2_DMA_Q|DBG)" run.log | tail -24
grep -q "^B2_DMA_Q PASS" run.log
