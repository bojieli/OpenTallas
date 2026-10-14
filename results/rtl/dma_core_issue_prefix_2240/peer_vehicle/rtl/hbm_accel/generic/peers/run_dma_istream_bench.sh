#!/bin/bash
# tb_hgi_dma_istream (record -> engines -> real HGI VM; el1011-hbm-b2: -GB2=1 four clusters): run_dma_istream_bench.sh OUT_DIR [-G...]
# PASS line: ISTREAM PASS FRONT <f>; HASH <hash of every word read back> (B2 = 0 / 1 must match).
set -u
O=$1; shift
S=$(cd "$(dirname "$0")/../../../.." && pwd)
V=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
P=$S/rtl/hbm_accel/generic/peers
mkdir -p "$O" && cd "$O" || exit 2
$V --binary -j 8 --top-module tb_hgi_dma_istream -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --timing -O1 "$@" \
  -y $S/rtl/hbm_accel/generic/vm -y $S/rtl/lib -y $S/rtl/hbm_accel/generic/peers \
  $S/rtl/lib/ot_rst_relay.sv $S/rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv \
  $S/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  $S/rtl/link/ot_fifo_sram_fwft.sv $S/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  $S/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  $S/rtl/hbm_accel/generic/adapters/ot_hgi_dma_record.sv $P/ot_hgi_dma_engines.sv $P/ot_hgi_dma_front.sv $P/ot_hgi_dma_back.sv \
  $P/ot_hgi_dma_mover.sv $P/ot_hgi_dma_mover_serial.sv $P/ot_hgi_dma_kvw.sv $P/ot_hgi_dma_mover_el.sv \
  $S/rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv $P/ot_hgi_b2_qrot.sv $P/tb_hgi_rlanes.sv $P/tb_hgi_dma_istream.sv --Mdir obj -o tb > build.log 2>&1 \
  || { echo "BUILD FAIL"; grep -m10 -E "%Error" build.log; exit 2; }
timeout 3600 ./obj/tb > run.log 2>&1
grep -E '^(ISTREAM|FATAL|HASH)' run.log | tail -20
grep -q "^ISTREAM PASS" run.log
