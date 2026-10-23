#!/bin/bash
set -u
mkdir -p "$1"; OUT=$(cd "$1" && pwd)
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$OUT/verilator.version" 2>&1
LA="--lane-ages results/rtl/qwen_layer_tput_1018/ctlm_prog/lane_ages_dv2f14bn.json"
python3 tools/qwen_layerbench/ctlm_image.py --out "$OUT/img0" $LA > "$OUT/compile_img0.txt" 2>&1 || exit 2
python3 tools/qwen_layerbench/ctlm_image.py --out "$OUT/imgh" $LA --lm-head > "$OUT/compile_imgh.txt" 2>&1 || exit 2
B=rtl/test/qwen_dv/tt_ctlm_prog_bench.py
for h in 0 1; do
 for v in base head m36 m37 b3 segmut; do
  img=imgh; mut=0; bm=0; defs=""
  case "$v" in base) img=img0;; m36) mut=36;; m37) mut=37;; b3) bm=3;; segmut) defs="--defs OT_SEG_MUT";; esac
  python3 "$B" --decode 3 --hard "$h" --work "$OUT/w_h${h}_${v}" --img "$OUT/$img" --mut "$mut" --bmut "$bm" $defs > "$OUT/h${h}_${v}.out" 2>&1
  echo "rc=$?" >> "$OUT/h${h}_${v}.out"
 done
done
for f in "$OUT"/h*.out; do echo "$f"; head -14 "$f"; done > "$OUT/summary.txt"
