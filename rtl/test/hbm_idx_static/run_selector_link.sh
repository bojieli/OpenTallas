#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-static-selector-proof}")
mkdir -p "$out"
python3 tools/hbm_idx_static_selector_vectors.py "$out"
for m in 0 1 2; do
 iverilog -g2012 -s tb_selector_link_static -Ptb_selector_link_static.MUT="$m" -o "$out/s$m.vvp" rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv rtl/test/hbm_idx_static/tb_selector_link_static.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$out/sbuild$m.log" 2>&1
 set +e
 (cd "$out"&&vvp "s$m.vvp") > "$out/srun$m.log" 2>&1
 rc=$?
 set -e
 cat "$out/srun$m.log"
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
done
