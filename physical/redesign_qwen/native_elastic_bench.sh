#!/bin/bash
set -u
mode=$1; out=$2; width=${3:-546}; depth=${4:-8}; mkdir -p "$out"
negative=0; [ "$mode" = neg ] && negative=2
iverilog -g2012 -s tb_qwen_native_elastic_relay -Ptb_qwen_native_elastic_relay.W="$width" \
  -Ptb_qwen_native_elastic_relay.NEG="$negative" -o "$out/test.vvp" \
  -Ptb_qwen_native_elastic_relay.DEPTH="$depth" \
  rtl/test/tb_qwen_native_elastic_relay.sv rtl/physical/ot_qwen_native_elastic_relay.sv \
  rtl/physical/ot_qwen_die_station.sv rtl/common/ot_link_credit.sv rtl/lib/ot_reset_sync.sv \
  > "$out/build.log" 2>&1 || { echo NATIVE_ELASTIC_BUILD_FAIL; exit 2; }
vvp "$out/test.vvp" > "$out/run.log" 2>&1
if [ "$mode" = pos ]; then
  grep -q '^PASS elastic' "$out/run.log" && { echo NATIVE_ELASTIC_PASS; exit 0; }
  echo NATIVE_ELASTIC_FAIL; exit 1
fi
grep -q '^NEG_DETECTED elastic' "$out/run.log" && { echo NATIVE_ELASTIC_NEG_DETECTED; exit 1; }
echo NATIVE_ELASTIC_NEG_MISSED; exit 0
