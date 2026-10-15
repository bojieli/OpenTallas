#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
owner="$d/ot_hbm_svc_prefetch_mapped4_offset_owner.sv"
for mode in 0 1;do
 iverilog -g2012 -s tb_hbm_svc_mapped4_offset_owner -Ptb_hbm_svc_mapped4_offset_owner.MODE=$mode -o "$out/owner$mode.vvp" "$owner" "$d/tb_hbm_svc_mapped4_offset_owner.sv"
 vvp "$out/owner$mode.vvp" > "$out/owner$mode.log"
done
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_burst_bank.sv" "$mem" "$d/ot_hbm_svc_native_stream_pc_lease.sv" "$d/ot_hbm_svc_native_sector_prefetch_stack.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$owner" "$d/ot_hbm_svc_prefetch_mapped4_offset_cdc.sv" "$d/tb_hbm_svc_mapped4_offset_native.sv")
for mode in 0 1;do
 iverilog -g2012 -s tb_hbm_svc_mapped4_offset_native -Ptb_hbm_svc_mapped4_offset_native.MODE=$mode -o "$out/native$mode.vvp" "${sources[@]}" > "$out/build$mode.log" 2>&1
done
for off in 4 12 4092 4096;do
 vvp "$out/native1.vvp" +OFFSET=$off +TOTAL=73 > "$out/offset$off.log"
done
vvp "$out/native0.vvp" +OFFSET=0 +TOTAL=272 > "$out/bootstrap.log"
for invalid in 1 2 3 4;do vvp "$out/native1.vvp" +INVALID=$invalid > "$out/invalid$invalid.log";done
cat "$out"/owner*.log "$out"/offset*.log "$out/bootstrap.log" "$out"/invalid*.log
