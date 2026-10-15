#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required};image=${2:?actual released image directory required};off=${3:?exact packed offset required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_burst_bank.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$d/ot_hbm_svc_native_stream_pc_lease.sv" "$d/ot_hbm_svc_native_sector_prefetch_stack.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/ot_hbm_svc_prefetch_mapped4_offset_owner.sv" "$d/ot_hbm_svc_prefetch_mapped4_offset_cdc.sv" "$d/tb_hbm_svc_mapped4_offset_install.sv")
iverilog -g2012 -s tb_hbm_svc_mapped4_offset_install -Ptb_hbm_svc_mapped4_offset_install.IMAGE_OFFSET="$off" -o "$out/install.vvp" "${sources[@]}" > "$out/build.log" 2>&1
vvp "$out/install.vvp" +DIR="$image" > "$out/positive.log"
grep -q 'MAPPED4_OFFSET_INSTALL PASS actual_WR=1836 real_ACK=1836 actual_RD=1836 exact_sectors=1836 actual_records=432' "$out/positive.log"
for mutant in WRONGADDR DROP EARLYACK;do
 if vvp "$out/install.vvp" +DIR="$image" +"$mutant" > "$out/$mutant.log";then echo "mutant unexpectedly passed $mutant";exit 1;fi
done
cat "$out/positive.log" "$out/WRONGADDR.log" "$out/DROP.log" "$out/EARLYACK.log"
