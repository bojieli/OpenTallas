#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:-0};mkdir -p "$out"
src=(rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/test/hbm_idx_static/tb_idx_tail_exact_0811.sv)
if [ ! -x "$out/obj/Vtb_idx_tail_exact_0811" ]; then
 OPENBLAS_NUM_THREADS=1 python3 tools/hbm_idx_tail_vectors_0811.py "$out"
 sha256sum "${src[@]}" tools/hbm_idx_tail_vectors_0811.py tools/hdc_golden_v41.py tools/hdc_golden.py tools/hdc_isa.py > "$out/sources.sha256"
 vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator;[ -x "$vl" ] || vl=verilator
 "$vl" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx_tail_exact_0811 --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1
else
 sha256sum -c "$out/sources.sha256" > "$out/source_check.log"
fi
(cd "$out" && "$out/obj/Vtb_idx_tail_exact_0811" +MUT="$mut")
