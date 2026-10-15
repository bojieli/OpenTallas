#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=${1:?output directory}
mkdir -p "$OUT/native"
for f in rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v;do
 git -C "$ROOT" show "HEAD:$f" > "$OUT/native/$(basename "$f")"
done
p=$ROOT/rtl/hbm_accel/generic/collective/p2p
for kind in 0 1;do
for mutant in 0 1;do
  iverilog -g2012 -s tb_hgi_coll_q_static_host_v4_elastic_rx -Ptb_hgi_coll_q_static_host_v4_elastic_rx.MUT="$mutant" \
   -Ptb_hgi_coll_q_static_host_v4_elastic_rx.PINGPONG="$kind" -o "$OUT/k${kind}m$mutant.vvp" \
   "$p/tb_hgi_coll_q_static_host_v4_elastic_rx.sv" "$p/ot_hfd_coll_q2_static_host_v4.sv" "$p/ot_hfd_coll_q2_static_host_v4_elastic_rx.sv" "$p/ot_hgi_coll_offdie_rx_block.sv" "$p/ot_hgi_coll_offdie_rx_pingpong.sv" "$p/ot_hfd_coll_q2_static_host_v4_elastic_rx_pingpong.sv" \
   "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv" "$p/ot_hgi_coll_static_issuer.sv" \
   "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_reduce_static.sv" \
   "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv" \
   "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv" \
   "$OUT/native/ot_qkvd_d2d_llr.sv" "$OUT/native/ot_qwen_crc_parallel.sv" \
   "$OUT/native/ot_hdc_fp32_add_lat.sv" "$OUT/native/ot_hdc_prefix.sv" "$OUT/native/ot_hdc_fastfp.sv" \
   "$OUT/native/ot_sram_1r1w_64x512_m1_r2c2.v" \
   > "$OUT/k${kind}m$mutant.compile.log" 2>&1 || { cat "$OUT/k${kind}m$mutant.compile.log";exit 2; }
  vvp "$OUT/k${kind}m$mutant.vvp" > "$OUT/k${kind}m$mutant.log" 2>&1
  cat "$OUT/k${kind}m$mutant.log"
  rg -q '^HCOLL_OFFDIE_RX_HOST_ADMISSION_PASS' "$OUT/k${kind}m$mutant.log"
  rm "$OUT/k${kind}m$mutant.vvp"
done
done
