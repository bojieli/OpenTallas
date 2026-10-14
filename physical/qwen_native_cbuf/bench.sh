#!/usr/bin/env bash
set -eu
OUT=$1; CASE=$2; IMG=${3:-physical/qwen_native_cbuf/images/layer0/crom.hex.gz}; mkdir -p "$OUT"
if [[ "$IMG" == *.gz ]];then gzip -dc "$IMG" > "$OUT/crom.hex";IMG="$OUT/crom.hex";fi
T=tb_qfd_cbuf_native_l0; MUT=0; LATERR=0
case "$CASE" in exact) ;; row_mut) MUT=1;; bank_mut) MUT=2;; latency_mut) LATERR=1;; *) exit 2;; esac
iverilog -g2012 -s "$T" -P"$T.MUT=$MUT" -P"$T.NTOK=1" -P"$T.RPS=1200" -P"$T.FLP=11" -P"$T.GRPS=1" -P"$T.TILE=1" -P"$T.LATERR=$LATERR" -o "$OUT/sim" \
 rtl/test/redesign_qwen/tb_qfd_cbuf_native_l0.sv rtl/physical/ot_qfd_su_cbuf_native_l0.sv \
 rtl/qwen_sys/redesign_qwen/ot_qfd_crom_lbuf.sv rtl/hdc/ot_hdc_delay.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$OUT/build.log" 2>&1
vvp "$OUT/sim" +CROM="$IMG" > "$OUT/run.log" 2>&1
line=$(grep -E '^(PASS|FAIL) cbuf_native_l0' "$OUT/run.log" | tail -1)
echo "$line"
case "$line" in PASS*)exit 0;; *)exit 1;;esac
