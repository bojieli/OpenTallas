#!/bin/bash
# HKV-HROOT 10-18: QM CDC fork CSR0 temporal bench (tb_hkv_cdc_csr_temporal): a legal 8-write host-credit burst of
# CSR0; every published share must be captured in ck with its own payload. Usage: csr_temporal.sh HOLD_ACK OUTDIR
# HOLD_ACK 1 (fork default) must PASS; 0 (legacy, no acknowledge) must FAIL.
set -euo pipefail
H=${1:?HOLD_ACK}; O=${2:?outdir}; mkdir -p "$O"
cd "$(dirname "$0")/../../../.."
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hkv_cdc_csr_temporal -GHOLD_ACK="$H" \
  --Mdir "$O/obj" rtl/test/qwen_host/tb_hkv_cdc_csr_temporal.sv \
  rtl/qwen_sys/host_cluster_cdc_20261018/qkd_hr_native_qm_cdc.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv \
  rtl/lib/ot_reset_sync.sv rtl/link/ot_link_afifo.sv rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v > "$O/build.log" 2>&1
"$O/obj/Vtb_hkv_cdc_csr_temporal"
