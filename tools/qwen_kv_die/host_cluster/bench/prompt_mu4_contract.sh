#!/bin/bash
set -eu
OUT=${1:-out_mu4_contract};mkdir -p "$OUT"
verilator --version
for m in 0 1 2 3;do
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hkv_mu4_record_pair -GMUT="$m" -Mdir "$OUT/obj$m" rtl/test/qwen_host/tb_hkv_mu4_record_pair.sv rtl/qwen_sys/mu_qwen_20261018/qkd_host_record_port_mu.sv rtl/qwen_sys/context_transport_20261014/qkd_host_record_port.sv rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv >"$OUT/build$m.log" 2>&1
 set +e
 "$OUT/obj$m/Vtb_hkv_mu4_record_pair" >"$OUT/m$m.log" 2>&1
 rc=$?
 set -e
 cat "$OUT/m$m.log"
 if [ "$m" = 0 ];then [ "$rc" = 0 ];grep -q 'MU4_RECORD_PAIR PASS' "$OUT/m$m.log";else [ "$rc" != 0 ];grep -q 'MU4_RECORD_PAIR FAIL' "$OUT/m$m.log";fi
done
echo 'MU4_RECORD_PAIR_SUITE PASS 4context 3causalmutants'
