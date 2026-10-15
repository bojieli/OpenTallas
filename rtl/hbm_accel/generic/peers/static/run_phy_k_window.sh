#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out="${1:?output directory}"
mkdir -p "$out"
if [[ -f ot_chip_v41x_hbm3e_phy.sv ]]; then
 sources=(ot_hdc_v41x_idx_hbm.sv ot_hdc_hbm_model.sv ot_chip_v41x_hbm3e_phy.sv tb_phy_k_window.sv)
else
 repo="$(git rev-parse --show-toplevel)"
 sources=("$repo/rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv" "$repo/rtl/hdc/kv/ot_hdc_hbm_model.sv" "$repo/rtl/chip/ot_chip_v41x_hbm3e_phy.sv" tb_phy_k_window.sv)
fi
for define in normal synthesis;do
 extra=();if [ "$define" = synthesis ];then extra=(-DSYNTHESIS);fi
 /usr/bin/time -v -o "$out/build-$define.time" verilator --binary --timing -j 4 -Wno-fatal "${extra[@]}" --top-module tb_phy_k_window --Mdir "$out/obj-$define" -o gate "${sources[@]}" > "$out/build-$define.log" 2>&1
 "$out/obj-$define/gate" > "$out/sim-$define.log" 2>&1
 grep -q 'PHY_K_WINDOW PASS' "$out/sim-$define.log"
 cat "$out/sim-$define.log"
done
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_phy_k_window_overflow --Mdir "$out/obj-overflow" -o gate "${sources[@]}" > "$out/build-overflow.log" 2>&1
if "$out/obj-overflow/gate" > "$out/sim-overflow.log" 2>&1;then echo 'window overflow not rejected';exit 1;fi
grep -q 'K window exceeds native address width' "$out/sim-overflow.log"
printf 'PASS K window guards including SYNTHESIS and parameteroverflow\n'
