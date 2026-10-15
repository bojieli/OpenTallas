#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv rtl/hdc/kv/ot_hdc_hbm_model.sv rtl/chip/ot_chip_v41x_hbm3e_phy.sv "$d/ot_hbm_svc_wb_block_cdc.sv" "$d/ot_hbm_svc_phy_mux.sv")
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_block_roundtrip --Mdir "$out/positive_obj" -o positive "${sources[@]}" "$d/ot_hbm_svc_prefetch_block_cdc.sv" "$d/tb_hbm_svc_block_roundtrip.sv" > "$out/build.log" 2>&1
"$out/positive_obj/positive" > "$out/positive.log"
grep -q 'BLOCK_ROUNDTRIP PASS actualPHY=1 preload=0' "$out/positive.log"
sed 's/\.r_addr_in(drain_row\[6:0\])/.r_addr_in(drain_row[6:0] ^ 7\x27d1)/' "$d/ot_hbm_svc_prefetch_block_cdc.sv" > "$out/mutant.sv"
if cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_prefetch_block_cdc.sv";then exit 1;fi
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_block_roundtrip --Mdir "$out/mutant_obj" -o mutant "${sources[@]}" "$out/mutant.sv" "$d/tb_hbm_svc_block_roundtrip.sv" > "$out/mutant_build.log" 2>&1
if "$out/mutant_obj/mutant" > "$out/mutant.log";then echo 'mutant passed unexpectedly';exit 1;fi
grep -q 'actual HBM roundtrip data' "$out/mutant.log"
cat "$out/positive.log"
echo 'BLOCK_ROUNDTRIP_MUTANT rejected real landing SRAM read-address corruption'
