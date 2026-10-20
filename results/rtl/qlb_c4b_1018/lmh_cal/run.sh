#!/bin/bash
# QLB-C4b/2 (10-18) LM-head segment calendar bench, run on the fleet (Verilator 5.050) from the staged source root.
#   run.sh OUT   (cwd = the staged worktree root)
# Images: img0 = the default decode image (no LM head; must stay 123/123 = the as-built behaviour at base 0),
#         imgh = ctlm_image.py --lm-head (LM-head programme at base 25: segment-G calendar + G XPF schedule).
# Variants (tt_ctlm_prog_bench.py, qfd_tt_ctlm_dv STAGE_ME 1 -> SEG_CAL 1):
#   img0: m0 PASS; bmut 1, bmut 2, mut 1 FAIL (the QLB-PROG mutants, unchanged)
#   imgh: m0 PASS; mut 9 (head calendar base-0-only gate), mut 10 (G XPF never starts), bmut 3 (G row 0 one cycle late),
#         defs OT_SEG_MUT (segment G reads the base-0 rows) FAIL
set -u
mkdir -p "$1"; OUT=$(cd "$1" && pwd)
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$OUT/verilator.version" 2>&1
LA="--lane-ages results/rtl/qwen_layer_tput_1018/ctlm_prog/lane_ages_dv2f14bn.json"
python3 tools/qwen_layerbench/ctlm_image.py --out "$OUT/img0" $LA > "$OUT/compile_img0.txt" 2>&1 || exit 2
python3 tools/qwen_layerbench/ctlm_image.py --out "$OUT/imgh" $LA --lm-head > "$OUT/compile_imgh.txt" 2>&1 || exit 2
B=rtl/test/qwen_dv/tt_ctlm_prog_bench.py
run() { n=$1; shift; python3 $B --decode 3 --work "$OUT/w_$n" "$@" > "$OUT/$n.out" 2>&1; echo "rc=$?" >> "$OUT/$n.out"; }
# builds are per (mut, defs); a bmut variant reuses its m0 work dir (and build)
( run img0_m0 --img "$OUT/img0" --mut 0 --bmut 0
  python3 $B --decode 3 --work "$OUT/w_img0_m0" --img "$OUT/img0" --mut 0 --bmut 1 > "$OUT/img0_b1.out" 2>&1; echo "rc=$?" >> "$OUT/img0_b1.out"
  python3 $B --decode 3 --work "$OUT/w_img0_m0" --img "$OUT/img0" --mut 0 --bmut 2 > "$OUT/img0_b2.out" 2>&1; echo "rc=$?" >> "$OUT/img0_b2.out" ) &
( run imgh_m0 --img "$OUT/imgh" --mut 0 --bmut 0
  python3 $B --decode 3 --work "$OUT/w_imgh_m0" --img "$OUT/imgh" --mut 0 --bmut 3 > "$OUT/imgh_b3.out" 2>&1; echo "rc=$?" >> "$OUT/imgh_b3.out" ) &
run imgh_mut9 --img "$OUT/imgh" --mut 9 --bmut 0 &
run imgh_mut10 --img "$OUT/imgh" --mut 10 --bmut 0 &
run imgh_segmut --img "$OUT/imgh" --mut 0 --bmut 0 --defs OT_SEG_MUT &
run img0_mut1 --img "$OUT/img0" --mut 1 --bmut 0 &
wait
for n in img0_m0 img0_b1 img0_b2 img0_mut1 imgh_m0 imgh_mut9 imgh_mut10 imgh_b3 imgh_segmut; do
  head -14 "$OUT/$n.out"; done > "$OUT/summary.txt"
# fleet source binding: every bench input on this host
{ cat rtl/test/qwen_dv/tt_ctlm_dv_sources.f; echo rtl/test/qwen_dv/tb_qfd_tt_ctlm_prog.sv; echo rtl/test/qwen_dv/main2.cpp
  echo rtl/test/qwen_dv/tt_ctlm_prog_bench.py; echo tools/qwen_layerbench/ctlm_image.py; cat results/rtl/qlb_c4b_1018/lmh_cal/compiler_inputs.txt; } |
  sort -u | xargs sha256sum > "$OUT/source.sha256"
find "$OUT" -name 'obj_*' -type d -prune -exec rm -rf {} +
exit 0
