#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output};mkdir -p "$out";out=$(cd "$out"&&pwd)
for mode in 2:1:1:0 1:1:1:0 0:1:1:0 2:0:1:0 2:1:0:0 2:1:1:1 2:1:1:2;do
 IFS=: read -r pipe enable inter mut <<< "$mode"
 iverilog -g2012 -s tb_qkd_host_ecc_pinvalid_equiv -Ptb_qkd_host_ecc_pinvalid_equiv.PIPE="$pipe" -Ptb_qkd_host_ecc_pinvalid_equiv.ENABLE="$enable" -Ptb_qkd_host_ecc_pinvalid_equiv.INTERLEAVED="$inter" -Ptb_qkd_host_ecc_pinvalid_equiv.PIN_MUT="$mut" -o "$out/unit-$mode" \
 rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/qwen_sys/host_20261013/ot_qfd_kv_landing_ecc_pinvalid_candidate.sv rtl/test/qwen_host/tb_qkd_host_ecc_pinvalid_equiv.sv > "$out/build-$mode.log" 2>&1
 set +e
 vvp "$out/unit-$mode" > "$out/run-$mode.log" 2>&1
 rc=$?
 set -e
 if [[ $mut == 0 ]];then [[ $rc == 0 ]];grep -q '^PASS ECC_PINVALID_EQUIV' "$out/run-$mode.log";else [[ $rc != 0 ]];grep -q 'PINVALID exact output/latency mismatch' "$out/run-$mode.log";fi
 cat "$out/run-$mode.log";rm "$out/unit-$mode"
done
