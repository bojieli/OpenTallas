#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd);cd "$R"
out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd)
top=${TOP:-qkd_host_rank_services}
vlt=${VERILATOR:-verilator}
"$vlt" --lint-only -O1 --top-module "$top" --Mdir "$out/obj" -Wno-fatal -GENABLE_SERVICE=1 -GENABLE_TOKEN=1 -GENABLE_NATIVE=1 \
 rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv rtl/qwen_sys/context_transport_20261014/qkd_host_record_port.sv rtl/qwen_sys/host_integrated_20261014/*.sv rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_epoch_allocator.sv rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_cohort.sv rtl/qwen_sys/split_20261014/qkd_hbm_boot_pc.sv rtl/qwen_sys/split_20261014/qkd_hbm_boot_static.sv rtl/qwen_sys/split_20261014/qkd_hbm_boot_static_completion.sv rtl/qwen_sys/split_20261014/qkd_static_completion_ownerdemux.sv rtl/test/qwen_host/qkd_host_board_port_fixture.sv rtl/qwen_sys/host_20261013/*.sv rtl/physical/ot_qkd_host_prompt_capture_pins.sv rtl/physical/ot_qfd_prompt_sram_capture.sv rtl/physical/ot_qwen_host_ctl.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/physical/ot_qwen_async_fifo_w.sv \
 rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv rtl/qwen_sys/ot_qwen_sys_rst_seq.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv \
 "$R/rtl/physical/ot_qfd_link_adp512_split.sv" "$R/rtl/qwen_sys/missing_masters_20261007/ot_qfd_link_adapter.sv" "$R/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv" \
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v" \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v > "$out/build.log" 2>&1 || { tail -n 100 "$out/build.log";exit 1; }
echo "PASS HOST_INTEGRATED_ELABORATE top=$top"
