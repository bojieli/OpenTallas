#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-keypack-proof}")
mkdir -p "$out"
python3 tools/hbm_idx_static_query_vectors.py "$out"
src=(rtl/hbm_accel/index/ot_hbm_idx_keypack_static.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/test/hbm_idx_static/tb_keypack_static.sv)
for m in 0 1 2 3;do
 iverilog -g2012 -s tb_keypack_static -Ptb_keypack_static.MUT="$m" -o "$out/k$m.vvp" "${src[@]}" > "$out/kbuild$m.log" 2>&1
 set +e
 (cd "$out"&&vvp "k$m.vvp") > "$out/krun$m.log" 2>&1
 rc=$?
 set -e
 cat "$out/krun$m.log"
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
done
