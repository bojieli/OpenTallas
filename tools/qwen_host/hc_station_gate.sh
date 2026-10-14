#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out"
for mut in 0 1;do
 iverilog -g2012 -s tb_qkd_host_hc_station -Ptb_qkd_host_hc_station.MUT="$mut" -o "$out/m$mut" rtl/qwen_sys/host_20261013/qkd_host_hc_station.sv rtl/test/qwen_host/tb_qkd_host_hc_station.sv
 if [[ $mut == 0 ]];then vvp "$out/m$mut" | tee "$out/positive.log";
 else if vvp "$out/m$mut" > "$out/mutant.log" 2>&1;then echo 'FAIL undetected raw hc payload mutant';exit 1;fi;cat "$out/mutant.log";fi
 rm "$out/m$mut"
done
