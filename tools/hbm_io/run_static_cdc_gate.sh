#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mkdir -p "$out"
for case in base slow fast drop corrupt absent early; do
  mut=0;ppm=0
  case "$case" in slow)ppm=300;;fast)ppm=-300;;drop)mut=1;;corrupt)mut=2;;absent)mut=3;;early)mut=4;;esac
  iverilog -g2012 -s tb_static_word_cdc -Ptb_static_word_cdc.MUT="$mut" -Ptb_static_word_cdc.WPPM="$ppm" -o "$out/$case.vvp" "$root/rtl/hbm_accel/io_static_20261015/ot_hbm_static_word_cdc.sv" "$root/rtl/hbm_accel/io_static_20261015/tb_static_word_cdc.sv"
  code=0
  vvp "$out/$case.vvp" > "$out/$case.log" 2>&1 || code=$?
  if [[ $mut == 0 ]];then
    [[ $code == 0 ]];grep -q 'PASS static word CDC words=4096' "$out/$case.log"
  else
    [[ $code != 0 ]];grep -q FATAL "$out/$case.log"
  fi
  cat "$out/$case.log"
done
