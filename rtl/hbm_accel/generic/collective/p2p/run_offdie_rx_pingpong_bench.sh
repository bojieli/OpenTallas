#!/usr/bin/env bash
set -euo pipefail
p=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(git -C "$p" rev-parse --show-toplevel)
out=${1:?output directory}
mkdir -p "$out/native"
for f in rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v;do
 git -C "$root" show "HEAD:$f" > "$out/native/$(basename "$f")"
done
sha256sum "$out"/native/* > "$out/native.sha256"
for m in 0 1 2 3;do
 iverilog -g2012 -s tb_hgi_coll_offdie_rx_pingpong -Ptb_hgi_coll_offdie_rx_pingpong.MUT="$m" -o "$out/m$m.vvp" \
 "$out"/native/*.sv "$out"/native/*.v \
 "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv" \
 "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv" \
 "$p/ot_hgi_coll_offdie_rx_block.sv" "$p/ot_hgi_coll_offdie_rx_pingpong.sv" "$p/tb_hgi_coll_offdie_rx_pingpong.sv" > "$out/m$m.compile.log" 2>&1
 if vvp "$out/m$m.vvp" > "$out/m$m.log" 2>&1;then
  cat "$out/m$m.log"
  if [[ $m != 0 ]];then echo 'mutant survived';exit 1;fi
  if [[ $m == 0 ]];then rg -q '^HCOLL_OFFDIE_RX_PINGPONG_PASS' "$out/m$m.log";else rg -q '^HCOLL_OFFDIE_RX_FAULT_PASS' "$out/m$m.log";fi
 else
  cat "$out/m$m.log"
  [[ $m != 0 ]] || exit 1
  rg -q 'FATAL:' "$out/m$m.log"
  echo "HCOLL_OFFDIE_RX_PINGPONG_MUTANT_REJECTED $m"
 fi
 rm "$out/m$m.vvp"
done

iverilog -g2012 -s tb_hgi_coll_offdie_rx_pingpong_faults -o "$out/faults.vvp" \
 "$out"/native/*.sv "$out"/native/*.v "$p/ot_hgi_coll_offdie_rx_block.sv" \
 "$p/ot_hgi_coll_offdie_rx_pingpong.sv" "$p/tb_hgi_coll_offdie_rx_pingpong_faults.sv" > "$out/faults.compile.log" 2>&1
vvp "$out/faults.vvp" > "$out/faults.log" 2>&1
cat "$out/faults.log"
rg -q '^HCOLL_OFFDIE_RX_PINGPONG_FAULTS_PASS' "$out/faults.log"
rm "$out/faults.vvp"
