#!/bin/bash
set -euo pipefail
sources=(rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_native_posted.sv rtl/qwen_sys/redesign_qwen/ot_qfd_native_q_reader.sv rtl/qwen_sys/redesign_qwen/ot_qfd_native_kv_commit_fence.sv rtl/qwen_sys/redesign_qwen/ot_qfd_native_kv_row_provider.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv rtl/test/qwen_su_kv_native/tb_provider.sv)
for fixture in positive row qbeat ack early qstale; do
 params=()
 case "$fixture" in
 row) params=(-Ptb_provider.MUT_ROW=1);;
 qbeat) params=(-Ptb_provider.MUT_QBEAT=1);;
 ack) params=(-Ptb_provider.MUT_ACK=1);;
 early) params=(-Ptb_provider.MUT_COMMIT=1);;
 qstale) params=(-Ptb_provider.MUT_RSP=1);;
 esac
 iverilog -g2012 -s tb_provider "${params[@]}" -o "$fixture.vvp" "${sources[@]}" 2>"$fixture.compile.log"
 vvp "$fixture.vvp" >"$fixture.log"
 tail -2 "$fixture.log"
 case "$fixture" in
 positive) rg -q '^PROVIDER_PASS' "$fixture.log";;
 row|qbeat) rg -q '^PROVIDER_FAIL data_errors[1-9]' "$fixture.log";;
 early) rg -q '^PROVIDER_FAIL .*early[1-9]' "$fixture.log";;
 ack) rg -q '^PROVIDER_ACK_REJECT_PASS' "$fixture.log";;
 qstale) rg -q '^PROVIDER_Q_REJECT_PASS' "$fixture.log";;
 esac
 done
