#!/bin/bash
set -euo pipefail
out=$1;mode=${2:-exact}
q=results/rtl/dma_hold_window_2240/peer_vehicle
cmp rtl/hbm_accel/generic/peers/ot_hgi_dma_kvw_hold_leaf_legacy.sv "$q/rtl/hbm_accel/generic/peers/ot_hgi_dma_kvw_hold_leaf_legacy.sv"
mkdir -p "$out"
args=(-GVR2=1 -GKVW=1 -GSVR2=0 -GKVB=1 -GKVB_MAX=630)
if [ "$mode" = mut ];then args+=(-GMUT=5);fi
J=8 bash "$q/tools/hgi_adapters/run_mover_kport.sh" "$out/build" "${args[@]}" 2>&1 | tee "$out/receipt.log"
grep -q 'MOVER-KPORT PASS' "$out/receipt.log"
