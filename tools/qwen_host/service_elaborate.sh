#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output};io=${2:?source-exact IO tree};mkdir -p "$out";out=$(cd "$out"&&pwd)
for mode in 0:0 1:0 1:1;do
 service=${mode%:*};native=${mode#*:}
 iverilog -g2012 -s qkd_host_service -Pqkd_host_service.ENABLE_SERVICE="$service" -Pqkd_host_service.ENABLE_NATIVE="$native" -o "$out/top-$mode" \
 rtl/qwen_sys/host_20261013/*.sv rtl/physical/ot_qkd_host_prompt_capture_pins.sv rtl/physical/ot_qfd_prompt_sram_capture.sv rtl/physical/ot_qwen_host_ctl.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/physical/ot_qwen_async_fifo_w.sv \
 rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv rtl/qwen_sys/ot_qwen_sys_rst_seq.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv \
 "$io/rtl/physical/ot_qfd_link_adp512_split.sv" "$io/rtl/qwen_sys/missing_masters_20261007/ot_qfd_link_adapter.sv" "$io/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv" \
 "$io/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v" \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v > "$out/build-$mode.log" 2>&1 || { cat "$out/build-$mode.log";exit 1; }
 rm "$out/top-$mode"
 printf 'PASS HOST_SERVICE_ELAB service=%s native=%s ELABORATION_ONLY\n' "$service" "$native"
done
