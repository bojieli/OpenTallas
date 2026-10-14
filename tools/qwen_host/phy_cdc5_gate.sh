#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
src=(rtl/qwen_sys/host_20261013/qkd_host_phy_cdc.sv rtl/qwen_sys/host_20261013/qkd_host_rx_pad.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/physical/ot_qwen_async_fifo_w.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/qwen_sys/host_20261013/qkd_host_phy_cdc5.sv rtl/qwen_sys/host_20261013/qkd_host_rx_pad5.sv rtl/test/qwen_host/tb_qkd_host_phy_cdc5.sv)
for mut in 0 1 2;do
 iverilog -g2012 -s tb_qkd_host_phy_cdc5 -Ptb_qkd_host_phy_cdc5.MUT="$mut" -o "$out/m$mut" "${src[@]}"
 if [[ $mut == 0 ]];then vvp "$out/m$mut" | tee "$out/positive.log";else
 if vvp "$out/m$mut" > "$out/mutant-$mut.log" 2>&1;then echo 'FAIL undetected PHY CDC mutant';exit 1;fi;cat "$out/mutant-$mut.log";fi
done

for mut in 0 1;do
 iverilog -g2012 -s tb_qkd_host_rx_pad5 -Ptb_qkd_host_rx_pad5.MUT="$mut" -o "$out/p$mut" rtl/qwen_sys/host_20261013/qkd_host_rx_pad5.sv rtl/test/qwen_host/tb_qkd_host_rx_pad5.sv
 if [[ $mut == 0 ]];then vvp "$out/p$mut" | tee "$out/pad-positive.log";else
 if vvp "$out/p$mut" > "$out/pad-mutant.log" 2>&1;then echo "FAIL undetected elasticpad payload mutant";exit 1;fi;cat "$out/pad-mutant.log";fi
 rm "$out/p$mut"
done
