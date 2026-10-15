#!/usr/bin/env bash
# tb_hgi_coll_p2p: central (ot_hfd_coll_r25gq) vs four quadrant engines (ot_hfd_coll_q) on G real dies.
# usage: run_p2p_bench.sh <outdir> <G> <tag> [plusargs...]; env CASES="qwen grm" DEFS="+define+MUT_Q | +define+SPMD" VFLAGS JOBS
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "$1"); G=$2; TAG=$3; shift 3
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective
SRC="rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv
 rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv
 rtl/hbm_accel/generic/ot_hgi_cfg.sv $C/ot_hgi_coll_decode.sv $C/ot_hgi_coll_amerge.sv $C/ot_hgi_coll_record.sv $C/ot_hgi_coll_ep.sv
 $C/rgx/ot_hgi_coll_rgx_src.sv $C/rgx/ot_hgi_coll_rgx_sink.sv $C/rgx/ot_hgi_coll_rgx_hbm.sv $C/rgx/ot_hgi_coll_rgx_snk.sv $C/rgx/ot_hgi_coll_rgx.sv rtl/hbm_accel/generic/peers/ot_hgi_hbm_lane.sv
 $C/tkm/ot_hgi_coll_tkm.sv $C/p2p/ot_hgi_coll_tkm_native.sv $C/tkm/ot_hgi_coll_tkm_seq_split.sv $C/tkm/ot_hgi_coll_tkm_seq_lane_core.sv $C/tkm/ot_hgi_coll_tkm_lane.sv $C/tkm/ot_hgi_coll_tkm_buffer.sv $C/tkm/ot_hgi_coll_tkm_packer.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 $C/ot_hfd_coll_r25gq.sv $C/p2p/ot_hgi_coll_qrec.sv $C/p2p/ot_hbm_accel_tu_endpoint_qpsg.sv $C/p2p/ot_hgi_coll_qep.sv $C/p2p/ot_hgi_coll_pring.sv $C/p2p/ot_hgi_coll_rgx_wtx.sv $C/p2p/ot_hgi_coll_crl.sv $C/p2p/ot_hfd_coll_q.sv $C/p2p/ot_hfd_coll_qm.sv
 $C/p2p/tb_hgi_coll_p2p.sv"
mkdir -p "$OUT"; cd "$ROOT"
"$VL" --binary --timing -O2 -j ${JOBS:-16} -Wno-fatal -Wno-lint -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  -Irtl/hbm_accel/generic +define+G=$G ${DEFS:-} ${VFLAGS:-} --top-module tb_hgi_coll_p2p --Mdir "$OUT/obj_$TAG" $SRC $C/p2p/f32add.c \
  > "$OUT/build_$TAG.log" 2>&1 || { tail -40 "$OUT/build_$TAG.log"; exit 2; }
# CASES="qwen grm" runs every case on the one build (the plusargs apply to each)
st=0
for c in ${CASES:-qwen}; do
  "$OUT/obj_$TAG/Vtb_hgi_coll_p2p" +CASE=$c "$@" > "$OUT/run_${TAG}_$c.log" 2>&1; rc=$?
  echo "== $c rc=$rc"; grep -E "^(REC|SEQ|IMAGES|RED_CARRY|PASS|FAIL|FAULT|TIMEOUT|STALL|DUMP|RC_|WDIFF|WCOUNT|WEXTRA|GEXP|REXP|MIRROR|\[)" "$OUT/run_${TAG}_$c.log" | head -60
  grep -q "^PASS HGI_COLL_P2P" "$OUT/run_${TAG}_$c.log" || st=1
done
exit $st
