#!/usr/bin/env bash
# hgi-unitrate: back-to-back DS gather sequence through ot_hgi_coll_ep (tb_hgi_coll_pipe).  usage: run_coll_pipe.sh <out>
# [plusargs...]; env PIPE=1 (pipelined endpoint), DEFS="+define+X ..." (mutants), TAG
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd); OUT=$(realpath -m "$1"); shift || true
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
TAG=${TAG:-$([ -n "${PIPE:-}" ] && echo pipe || echo base)}
D="${DEFS:-}"; [ -n "${PIPE:-}" ] && D="$D +define+PIPE"
SRC="rtl/hbm_accel/generic/collective/ot_hgi_coll_ep.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv
 rtl/hbm_accel/generic/collective/ot_hgi_coll_record.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_decode.sv
 rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv
 rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv
 rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/link/ot_link_afifo.sv rtl/hbm_accel/generic/ot_hgi_cfg.sv rtl/hbm_accel/generic/collective/tb_hgi_coll_pipe.sv"
mkdir -p "$OUT"; cd "$ROOT"
"$VL" --binary --timing -O2 -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  -Irtl/hbm_accel/generic --top-module tb_hgi_coll_pipe --Mdir "$OUT/obj_$TAG" $D $SRC > "$OUT/build_$TAG.log" 2>&1 || { tail -30 "$OUT/build_$TAG.log"; exit 2; }
"$OUT/obj_$TAG/Vtb_hgi_coll_pipe" "$@" | tee "$OUT/run_$TAG.log" | tail -30
