#!/usr/bin/env bash
set -eu
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-query-static-proof}")
mkdir -p "$out"
python3 tools/hbm_idx_static_query_vectors.py "$out"
for m in 0 1 2 3; do
  iverilog -g2012 -s tb_query_static -Ptb_query_static.MUT="$m" -o "$out/q$m.vvp" rtl/hbm_accel/index/ot_hbm_idx_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/test/hbm_idx_static/tb_query_static.sv > "$out/qbuild$m.log" 2>&1
  set +e
  (cd "$out" && vvp "q$m.vvp") > "$out/qrun$m.log" 2>&1
  rc=$?
  set -e
  cat "$out/qrun$m.log"
  if [ "$m" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
done
