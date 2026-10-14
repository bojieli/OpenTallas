#!/bin/bash
# Exact record semantics AND immutable-flat request payload/order equivalence.
set -euo pipefail
out=$1
root=$(cd "$(dirname "$0")/../../../.." && pwd)
bench=$root/rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh
TB_ARGS=+DMA_Q5_TRACE bash "$bench" "$out/partition"
TB_ARGS=+DMA_Q5_TRACE bash "$bench" "$out/flat" -GFLAT=1
python3 "$root/rtl/test/hbm_accel/b2_dma/compare_q5_ports.py" "$out/flat/run.log" "$out/partition/run.log"
