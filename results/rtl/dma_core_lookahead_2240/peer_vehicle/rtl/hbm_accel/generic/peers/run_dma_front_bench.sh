#!/bin/bash
# ot_hgi_dma_front unit bench (tb_hgi_dma_front): run_dma_front_bench.sh OUT_DIR [extra -G... / +args after --]
# PASS line: PASS HGI_DMA_FRONT ...; HASH <image hash>.  B2: -GB2=1 (four fronts), -GS4=1 (B2 = 0 reference for the hash).
set -u
O=$1; shift
S=$(cd "$(dirname "$0")/../../../.." && pwd)
V=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
G=(); P=(); for a in "$@"; do case $a in +*) P+=("$a");; *) G+=("$a");; esac; done
mkdir -p "$O" && cd "$O" || exit 2
$V --binary -j 8 --top-module tb_hgi_dma_front -Wno-fatal -Wno-lint -Wno-style --timing -O2 "${G[@]}" \
  $S/rtl/lib/ot_rst_relay.sv $S/rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv \
  $S/rtl/hbm_accel/generic/peers/ot_hgi_dma_front.sv $S/rtl/hbm_accel/generic/peers/tb_hgi_dma_front.sv --Mdir obj -o tb > build.log 2>&1 \
  || { echo "BUILD FAIL"; tail -20 build.log; exit 2; }
timeout 3600 ./obj/tb "${P[@]}" > run.log 2>&1
grep -E '^(PASS|FATAL|FAIL|HASH|B2|LOAD|ILOAD)' run.log | tail -30
grep -q "^PASS HGI_DMA_FRONT" run.log
