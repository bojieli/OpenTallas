#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
src=(rtl/qwen_sys/host_20261013/qkd_host_qm_ingress16_service.sv rtl/qwen_sys/host_20261013/qkd_host_qm_credit_pacer.sv rtl/qwen_sys/host_20261013/qkd_host_qm_clock_bridge_service.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/physical/ot_qwen_async_fifo_w.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/test/qwen_host/tb_qkd_host_qm_clock_bridge_service.sv)
for mut in 0 1 2 3 4;do
 iverilog -g2012 -s tb_qkd_host_qm_clock_bridge_service -Ptb_qkd_host_qm_clock_bridge_service.MUT="$mut" -o "$out/m$mut" "${src[@]}" > "$out/build-$mut.log" 2>&1
 if [[ $mut == 0 ]];then vvp "$out/m$mut" | tee "$out/positive.log";grep -q '^PASS QM_EPOCH_GATED_CLOCK_BRIDGE' "$out/positive.log";else
  if vvp "$out/m$mut" > "$out/mutant-$mut.log" 2>&1;then echo "FAIL undetected QM bridge mutant $mut";exit 1;fi
  grep -q '^FATAL:' "$out/mutant-$mut.log";cat "$out/mutant-$mut.log"
 fi
 rm "$out/m$mut"
done
