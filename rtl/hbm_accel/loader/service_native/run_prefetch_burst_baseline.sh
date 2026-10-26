#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_prefetch_burst_baseline --Mdir "$out/obj" -o baseline rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv rtl/hdc/kv/ot_hdc_hbm_model.sv rtl/chip/ot_chip_v41x_hbm3e_phy.sv "$d/tb_hbm_prefetch_burst_baseline.sv" > "$out/build.log" 2>&1
"$out/obj/baseline" > "$out/positive.log"
grep -q 'PASS immutable_actual_PHY_burst_baseline' "$out/positive.log"
cat "$out/positive.log"
