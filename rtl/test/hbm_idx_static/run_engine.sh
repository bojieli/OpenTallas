#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
out=$(realpath -m "${1:-/tmp/hbm-idx-engine-static-proof}")
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
[ -x "$vl" ] || vl=verilator
src=(rtl/hbm_accel/index/ot_hbm_idx_engine_static.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/test/hbm_idx_static/tb_idx_engine_static.sv rtl/test/hbm_idx_static/engine.vlt)
mkdir -p "$out"
for m in 0 2; do
 "$vl" --hierarchical --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx_engine_static -GMUT="$m" --Mdir "$out/engine$m" "${src[@]}" > "$out/ebuild$m.log" 2>&1
 set +e
 "$out/engine$m/Vtb_idx_engine_static" > "$out/erun$m.log" 2>&1
 rc=$?
 set -e
 cat "$out/erun$m.log"
 if [ "$m" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
done
