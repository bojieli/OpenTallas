#!/usr/bin/env bash
set -eu
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=${1:?output directory required}
mkdir -p "$out"
for m in 0 1 2; do
  iverilog -g2012 -s tb_idx_meta_delay -Ptb_idx_meta_delay.MUT=$m -o "$out/m$m.vvp" rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv rtl/test/hbm_idx_static/tb_idx_meta_delay.sv > "$out/build$m.log" 2>&1
  set +e
  vvp "$out/m$m.vvp" > "$out/run$m.log" 2>&1
  rc=$?
  set -e
  cat "$out/run$m.log"
  if [ "$m" = 0 ]; then [ "$rc" = 0 ]; else [ "$rc" != 0 ]; fi
done
sha256sum rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/index/ot_hbm_idx_score_static.sv rtl/test/hbm_idx_static/tb_idx_meta_delay.sv > "$out/sources.sha256"
echo 'IDX_META_DELAY GATE PASS'
