#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=${1:?output directory}
mkdir -p "$OUT"
p=$ROOT/rtl/hbm_accel/generic/collective/p2p
for mutant in 0 1 2;do
  iverilog -g2012 -s tb_hgi_coll_q_static_v2_reduce -Ptb_hgi_coll_q_static_v2_reduce.MUT="$mutant" \
   -o "$OUT/m$mutant.vvp" \
   "$p/tb_hgi_coll_q_static_v2_reduce.sv" "$p/ot_hfd_coll_q_static_v2.sv" "$p/ot_hgi_coll_static_issuer.sv" \
   "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_reduce_static.sv" \
   "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_seq.sv" "$p/ot_hgi_coll_static_seq_ctl.sv" \
   "$ROOT/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$ROOT/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv" \
   "$ROOT/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv" "$ROOT/rtl/hdc/ot_hdc_fastfp.sv" \
   "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
   > "$OUT/m$mutant.compile.log" 2>&1 || { cat "$OUT/m$mutant.compile.log";exit 2; }
  if vvp "$OUT/m$mutant.vvp" > "$OUT/m$mutant.log" 2>&1;then
   cat "$OUT/m$mutant.log"
   [[ "$mutant" == 0 ]] || { echo 'mutant survived';exit 1; }
   grep -q '^HCOLL_Q2_V2_NATIVE_REDUCE PASS' "$OUT/m$mutant.log"
  else
   cat "$OUT/m$mutant.log"
   [[ "$mutant" != 0 ]] || exit 1
   grep -q 'FATAL:' "$OUT/m$mutant.log"
   echo "V2 reduction mutant $mutant rejected"
  fi
  rm "$OUT/m$mutant.vvp"
done

iverilog -g2012 -s tb_hgi_coll_v2_seqface -o "$OUT/seqface.vvp" \
 "$p/tb_hgi_coll_v2_seqface.sv" "$p/ot_hfd_coll_q_static_v2.sv"
vvp "$OUT/seqface.vvp" > "$OUT/seqface.log" 2>&1
cat "$OUT/seqface.log"
grep -q '^HCOLL_V2_SEQFACE PASS' "$OUT/seqface.log"
rm "$OUT/seqface.vvp"
