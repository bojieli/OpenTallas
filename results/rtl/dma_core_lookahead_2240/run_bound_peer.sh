#!/bin/bash
set -euo pipefail
out=$1;mode=${2:-exact}
root=$(pwd)
q=results/rtl/dma_core_lookahead_2240/peer_vehicle
cmp rtl/hbm_accel/generic/peers/ot_hgi_dma_kvw_core_reg_kq.sv "$q/rtl/hbm_accel/generic/peers/ot_hgi_dma_kvw_core_reg_kq.sv"
if [ "$mode" = exact ]; then
 bash "$q/rtl/test/hbm_accel/b2_dma/run_dma_q5_partition_gate.sh" "$out"
else
 case "$mode" in seam[1-7]) arg="-GMUT_SEAM=${mode#seam}";; pin) arg=-GMUT_CORE_PIN=1;; look) arg=-GMUT_CORE_LOOK=1;; *) exit 2;; esac
 bash "$q/rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh" "$out" -GNREC=4 "$arg"
fi
