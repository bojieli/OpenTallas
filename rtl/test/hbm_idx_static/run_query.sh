#!/usr/bin/env bash
# Unit bench of the tile CORES (ot_hbm_idx_*_static_core, unchanged arithmetic); the pin-registered tiles are benched
# in run_scheduled.sh (calendar + parent from the compiled program).
set -eu
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-query-static-proof}")
mkdir -p "$out"
python3 tools/hbm_idx_static_query_vectors.py "$out"
# Optional 2nd arg MUT: run only that variant and exit with its own status (closure-job pass / fail benches).
single=${2:-}
for m in ${single:-0 1 2 3}; do
  iverilog -g2012 -s tb_query_static -Ptb_query_static.MUT="$m" -o "$out/q$m.vvp" rtl/hbm_accel/index/ot_hbm_idx_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/test/hbm_idx_static/tb_query_static.sv > "$out/qbuild$m.log" 2>&1
  set +e
  (cd "$out" && vvp "q$m.vvp") > "$out/qrun$m.log" 2>&1
  rc=$?
  set -e
  cat "$out/qrun$m.log"
  if [ -n "$single" ]; then exit "$rc"; fi
  if [ "$m" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
done
