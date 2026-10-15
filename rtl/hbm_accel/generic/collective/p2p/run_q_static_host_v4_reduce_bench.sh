#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=${1:?output directory}
mkdir -p "$OUT"
p=$ROOT/rtl/hbm_accel/generic/collective/p2p
for mutant in 0 1 2;do
  iverilog -g2012 -s tb_hgi_coll_q_static_host_v4_reduce -Ptb_hgi_coll_q_static_host_v4_reduce.MUT="$mutant" \
   -o "$OUT/m$mutant.vvp" \
   "$p/tb_hgi_coll_q_static_host_v4_reduce.sv" "$p/ot_hfd_coll_q2_static_host_v4.sv" \
   "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv" "$p/ot_hgi_coll_static_issuer.sv" \
   "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_reduce_static.sv" \
   "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv" \
   "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv" \
   "$ROOT/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$ROOT/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv" \
   "$ROOT/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv" "$ROOT/rtl/hdc/ot_hdc_fastfp.sv" \
   "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
   > "$OUT/m$mutant.compile.log" 2>&1 || { cat "$OUT/m$mutant.compile.log";exit 2; }
  if vvp "$OUT/m$mutant.vvp" > "$OUT/m$mutant.log" 2>&1;then
   cat "$OUT/m$mutant.log"
   [[ "$mutant" == 0 ]] || { echo 'mutant survived';exit 1; }
   grep -q '^HCOLL_Q2_HOST_V4_NATIVE_REDUCE PASS' "$OUT/m$mutant.log"
  else
   cat "$OUT/m$mutant.log"
   [[ "$mutant" != 0 ]] || exit 1
   grep -q 'FATAL:' "$OUT/m$mutant.log"
   echo "Host V4 reduction mutant $mutant rejected"
  fi
  rm "$OUT/m$mutant.vvp"
done
