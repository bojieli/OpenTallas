#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
src=(rtl/qwen_sys/host_20261013/qkd_host_commit_order.sv rtl/qwen_sys/host_20261013/qkd_host_ingest_chain.sv rtl/qwen_sys/host_20261013/qkd_host_ingest_chain_splitboot.sv rtl/qwen_sys/host_20261013/qkd_host_ingest_map.sv rtl/qwen_sys/host_20261013/qkd_host_ingest_station.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc_emback.sv rtl/qwen_sys/host_20261013/qkd_host_boot_dispatch.sv rtl/test/qwen_host/tb_qkd_host_splitboot_chain.sv)
for hot in 0 1;do
 iverilog -g2012 -s tb_qkd_host_splitboot_chain -Ptb_qkd_host_splitboot_chain.HOT="$hot" -o "$out/h$hot" "${src[@]}"
 vvp "$out/h$hot" | tee "$out/hot-$hot.log"
done
iverilog -g2012 -s tb_qkd_host_splitboot_chain -Ptb_qkd_host_splitboot_chain.MUT=1 -o "$out/mut" "${src[@]}"
if vvp "$out/mut" > "$out/mutant.log" 2>&1;then echo 'FAIL undetected physical completion mutant';exit 1;fi
cat "$out/mutant.log"
echo PASS HOST_SPLITBOOT_CHAIN_EXACT_AND_MUTANT
