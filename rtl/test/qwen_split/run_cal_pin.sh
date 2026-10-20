#!/bin/bash
# run_cal_pin.sh OUT [MUT] [MU]
#   MU=0 (default): the production calendar sequencer (ot_qwen_d2d_cal_seq_dies.sv + d2d_cal_image.svh), kit _ep3.
#   MU=1 (KV-DCAL-MU 10-19, kit qkd_d2d_cal_seq_pin_mu): ot_qwen_d2d_cal_seq_dies_mu.sv + d2d_cal_image_mu.svh; the tb
#        includes the MU image too, and the MU image's TXDP lines must equal the production image's (same die seam).
#   MUT 1: EP_SKEW anchor one edge early (-> CALPIN_FAIL compiled start)
#   MUT 2 (MU only): DUT built from the production dies file while the tb expects the MU image (-> CALPIN_FAIL boot control word)
#   MUT 3 (MU only): stale MU image with TXDP_K 0x03030417 [23] (-> CALPIN_FAIL txdp)
set -euo pipefail
out=$(realpath -m "$1");mut=${2:-0};mu=${3:-0}
mkdir -p "$out"
src=rtl/qwen_sys/d2d_static_20261015
img=d2d_cal_image.svh;dies=ot_qwen_d2d_cal_seq_dies.sv;inc="-I$src";def=""
if [ "$mu" = 1 ]; then
  img=d2d_cal_image_mu.svh;dies=ot_qwen_d2d_cal_seq_dies_mu.sv;def="-DCALPIN_MU"
  [ "$mut" = 2 ] && dies=ot_qwen_d2d_cal_seq_dies.sv
  if [ "$mut" = 3 ]; then
    mkdir -p "$out/stale"
    sed "s/D2D_TXDP_K = 32'h03030415/D2D_TXDP_K = 32'h03030417/" "$src/$img" > "$out/stale/$img"
    inc="-I$out/stale -I$src"
  fi
  imgf=$src/$img; [ "$mut" = 3 ] && imgf=$out/stale/$img
  if ! diff <(grep -o "D2D_TXDP_[CK] = 32'h[0-9a-f]*" "$src/d2d_cal_image.svh") <(grep -o "D2D_TXDP_[CK] = 32'h[0-9a-f]*" "$imgf") > "$out/txdp.diff"; then
    cat "$out/txdp.diff"; echo "CALPIN_FAIL txdp: $img TXDP lines differ from the production d2d_cal_image.svh"; exit 1
  fi
  echo "CALPIN_TXDP_MATCH $(grep -o "D2D_TXDP_K = 32'h[0-9a-f]*" "$imgf")"
fi
sha256sum "$src"/{qkd_d2d_cal_seq_pin.sv,ot_qwen_d2d_cal_seq.sv,$dies,$img,d2d_cal_image.svh} rtl/test/qwen_split/tb_qkd_cal_pin.sv > "$out/source.sha256"
iverilog -g2012 $def $inc -s tb_qkd_cal_pin -Ptb_qkd_cal_pin.MUT="$((mut==1))" -o "$out/test.vvp" "$src/qkd_d2d_cal_seq_pin.sv" "$src/ot_qwen_d2d_cal_seq.sv" "$src/$dies" rtl/test/qwen_split/tb_qkd_cal_pin.sv > "$out/build.log" 2>&1 || { cat "$out/build.log"; exit 1; }
vvp -n "$out/test.vvp" > "$out/run.log" 2>&1 || { cat "$out/run.log"; exit 1; }
cat "$out/run.log"
grep -q '^CALPIN_PASS starts74 layers72 token3start1' "$out/run.log"
