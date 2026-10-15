#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
fifo=rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv
iverilog -g2012 -s tb_hbm_svc_wb_block_cdc -o "$out/positive.vvp" "$mem" "$fifo" rtl/lib/ot_reset_sync.sv "$d/ot_hbm_svc_wb_block_cdc.sv" "$d/tb_hbm_svc_wb_block_cdc.sv"
vvp "$out/positive.vvp" > "$out/positive.log"
grep -q 'WB_BLOCK_CDC PASS' "$out/positive.log"
vvp "$out/positive.vvp" +resets > "$out/resets.log"
grep -q 'WB_BLOCK_CDC_RESETS PASS' "$out/resets.log"
vvp "$out/positive.vvp" +tail > "$out/tail.log"
grep -q 'WB_BLOCK_CDC_TAIL PASS' "$out/tail.log"
vvp "$out/positive.vvp" +faults > "$out/faults.log"
grep -q 'WB_BLOCK_CDC_FAULTS PASS' "$out/faults.log"
sed 's/sector\[6:2\]\^sector\[11:7\]\^sector\[16:12\]/sector[4:0]/' "$d/ot_hbm_svc_wb_block_cdc.sv" > "$out/mutant.sv"
if cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_wb_block_cdc.sv";then echo 'mutant not applied';exit 1;fi
iverilog -g2012 -s tb_hbm_svc_wb_block_cdc -o "$out/mutant.vvp" "$mem" "$fifo" rtl/lib/ot_reset_sync.sv "$out/mutant.sv" "$d/tb_hbm_svc_wb_block_cdc.sv"
if vvp "$out/mutant.vvp" > "$out/mutant.log";then echo 'mutant unexpectedly passed';exit 1;fi
grep -q 'XOR PC mismatch' "$out/mutant.log"
cat "$out/positive.log" "$out/tail.log" "$out/faults.log" "$out/resets.log"
echo 'WB_BLOCK_CDC_MUTANT rejected incorrect low5 PC mapping'
