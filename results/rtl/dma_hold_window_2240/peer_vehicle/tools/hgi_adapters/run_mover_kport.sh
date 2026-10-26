#!/usr/bin/env bash
# hbm-fq/dma (2026-10-11): build + run tb_hgi_mover_kport (the mover on the REAL loader kport + four svc stacks, the VM DMA
# read group model).  usage: run_mover_kport.sh <outdir> [-Gname=value ...]   (e.g. -GVR2=1 -GKVW=1 -GKVB=1 -GKVB_MAX=630)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$(realpath -m "$1"); shift
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
TAG=$(echo "$*" | tr -c 'A-Za-z0-9=_\n' '_' | tr -d '\n'); TAG=${TAG:-default}
S="rtl/hbm_accel/generic/peers/ot_hgi_dma_mover.sv rtl/hbm_accel/generic/peers/ot_hgi_dma_mover_serial.sv
   rtl/hbm_accel/generic/peers/ot_hgi_dma_kvw.sv rtl/hbm_accel/generic/peers/ot_hgi_dma_kvw_hold_leaf_legacy.sv rtl/hbm_accel/generic/peers/ot_hgi_dma_mover_el.sv rtl/lib/ot_rst_relay.sv
   rtl/hbm_accel/loader/service_native/ot_hfd_loader_kport.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_core_native.sv
   physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv
   physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v rtl/hbm_accel/generic/peers/tb_hgi_mover_kport.sv"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN --top-module tb_hgi_mover_kport \
  -y rtl/hbm_accel/loader/service_native -y physical/hbm_accel_die_views/svc/rtl -y rtl/hbm_accel/service -y rtl/hbm_accel/ingest \
  -y rtl/hbm_accel/loader -y rtl/lib -y rtl/hdc "$@" -Mdir "$OUT/obj_$TAG" $S -j ${J:-8} > "$OUT/build_$TAG.log" 2>&1 \
  || { tail -30 "$OUT/build_$TAG.log"; exit 2; }
"$OUT/obj_$TAG/Vtb_hgi_mover_kport" | tee "$OUT/run_$TAG.log" | grep -E "RATE|KVWB|PASS|FAIL" | tail -40
