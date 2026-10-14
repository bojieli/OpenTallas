#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
for mut in 0 1;do
 iverilog -g2012 -s tb_qkd_host_commit_order -Ptb_qkd_host_commit_order.MUT="$mut" -o "$out/m$mut" rtl/qwen_sys/host_20261013/qkd_host_commit_order.sv rtl/test/qwen_host/tb_qkd_host_commit_order.sv
 if [[ $mut == 0 ]];then vvp "$out/m$mut" | tee "$out/positive.log";else
 if vvp "$out/m$mut" > "$out/mutant.log" 2>&1;then echo 'FAIL undetected premature prefix mutant';exit 1;fi;cat "$out/mutant.log";fi
done
