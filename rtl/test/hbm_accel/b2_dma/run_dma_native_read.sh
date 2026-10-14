#!/bin/bash
set -euo pipefail
out=$1;shift
root=$(cd "$(dirname "$0")/../../../.." && pwd)
mkdir -p "$out";cd "$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --binary -j 8 --timing -Wno-fatal -Wno-MULTIDRIVEN --top-module tb_dma_native_read "$@" \
 "$root/rtl/hbm_accel/generic/peers/ot_hgi_dma_native_read.sv" "$root/rtl/test/hbm_accel/b2_dma/tb_dma_native_read.sv" --Mdir obj -o tb > build.log 2>&1
./obj/tb > run.log 2>&1
rg '^DMA_NATIVE (PASS|FAIL)' run.log
rg -q '^DMA_NATIVE PASS' run.log
