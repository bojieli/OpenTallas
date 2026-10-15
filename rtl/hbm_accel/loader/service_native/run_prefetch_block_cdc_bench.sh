#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$mem" rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv rtl/hdc/kv/ot_hdc_hbm_model.sv rtl/chip/ot_chip_v41x_hbm3e_phy.sv)
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_prefetch_block_cdc --Mdir "$out/positive_obj" -o positive "${sources[@]}" "$d/ot_hbm_svc_prefetch_block_cdc.sv" "$d/tb_hbm_svc_prefetch_block_cdc.sv" > "$out/build.log" 2>&1
for phase in 137 773; do
  "$out/positive_obj/positive" +PHASE=$phase > "$out/phase_$phase.log"
  grep -q 'PASS PREFETCH_CDC actualPHY' "$out/phase_$phase.log"
done
"$out/positive_obj/positive" +BADTAG > "$out/wrong_tag.log"
grep -q 'PASS wrong response epoch rejected' "$out/wrong_tag.log"
sed 's/pc_of=s\[6:2\]\^s\[11:7\]\^s\[16:12\]/pc_of=s[4:0]/' "$d/ot_hbm_svc_prefetch_block_cdc.sv" > "$out/mutant.sv"
if cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_prefetch_block_cdc.sv";then echo 'mutant not applied';exit 1;fi
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_prefetch_block_cdc --Mdir "$out/mutant_obj" -o mutant "${sources[@]}" "$out/mutant.sv" "$d/tb_hbm_svc_prefetch_block_cdc.sv" > "$out/mutant_build.log" 2>&1
if "$out/mutant_obj/mutant" > "$out/mutant.log";then echo 'wrong low5 PC mutant unexpectedly passed';exit 1;fi
grep -q 'actual XOR PC mismatch' "$out/mutant.log"
cat "$out/phase_137.log" "$out/phase_773.log" "$out/wrong_tag.log"
echo 'PREFETCH_CDC MUTANT rejected actual-PC routing corruption'
