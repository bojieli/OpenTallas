#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd)
for mode in 0:0 21:0 0:1 22:1;do
 IFS=: read -r mut bad <<< "$mode"
 iverilog -g2012 -s tb_qkd_host_token_peer_permit -Ptb_qkd_host_token_peer_permit.MUT="$mut" -Ptb_qkd_host_token_peer_permit.BAD="$bad" -o "$out/unit-$mode" \
 rtl/qwen_sys/host_20261013/qkd_host_ctrl_token_service_packet.sv rtl/qwen_sys/host_20261013/qkd_host_qm_ingress16_service.sv rtl/qwen_sys/host_20261013/qkd_host_service_guard.sv rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv rtl/test/qwen_host/tb_qkd_host_token_peer_permit.sv > "$out/build-$mode.log" 2>&1
 set +e
 vvp "$out/unit-$mode" > "$out/run-$mode.log" 2>&1
 rc=$?
 set -e
 if [[ $mut == 0 ]];then [[ $rc == 0 ]];grep -q '^PASS TOKEN_PEER_PERMIT' "$out/run-$mode.log";else [[ $rc != 0 ]];grep -q FATAL "$out/run-$mode.log";fi
 cat "$out/run-$mode.log"
 rm "$out/unit-$mode"
done
