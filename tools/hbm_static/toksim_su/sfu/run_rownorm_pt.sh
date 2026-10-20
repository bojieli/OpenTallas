#!/bin/bash
# HBM-SUFIX (b) 10-19: ROW_NORM sum of squares on the reducer PRE-TREE bench (tb_hbm_su_red_pretree, RTL @1dad69123 =
# closed hbm_su_pretree_s_1018-p3), Verilator 5.050.  Run from the bundle root.  usage: run_rownorm_pt.sh OUT
set -euo pipefail
OUT=$(realpath -m "$1"); mkdir -p "$OUT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; "$VL" --version > "$OUT/verilator.txt"
S=rtl/hbm_accel/generic/adapters/static_su
src=($S/reduction/ot_hbm_su_red_pretree.sv $S/top/ot_hbm_su_static_qcore_r5.sv $S/reduction/ot_hbm_su_reduce_static.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/test/hbm_accel/generic/tb_hbm_su_red_pretree.sv)
sha256sum "${src[@]}" tools/hbm_static/su_pretree_lower.py tools/hbm_static/toksim_su/sfu/rownorm_pt_bench.py > "$OUT/sources.sha256"
for mut in 0 1 512 1024; do
 "$VL" --binary --timing -j 8 --top-module tb_hbm_su_red_pretree -GMUT=$mut -Wno-fatal -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC \
  -DOT_FP_DATA_NORST --Mdir "$OUT/obj$mut" -o vtb "${src[@]}" > "$OUT/build$mut.log" 2>&1 || { tail -30 "$OUT/build$mut.log"; exit 2; }
done
for c in d4096_q8 d4096_q32 seg128_q2 seg128_k1; do
 python3 tools/hbm_static/toksim_su/sfu/rownorm_pt_bench.py "$OUT/$c" $c > "$OUT/$c.compile.txt"
 # ROW_NORM shapes: MUT 0 must PASS; MUT 512 (tree operand one edge late) must FAIL on the exact-edge check
 for mut in 0 512; do (cd "$OUT/$c" && "$OUT/obj$mut/vtb" $(cat plusargs.txt)) > "$OUT/$c.mut$mut.log" 2>&1 || true; done
 echo "== $c $(cut -c1-400 "$OUT/$c.compile.txt")"; for mut in 0 512; do echo "  mut$mut: $(grep -E '^(PASS|FAIL)' "$OUT/$c.mut$mut.log")"; done
done
# order witnesses on the same builds: the HH-6 bench stimulus (mixed-sign, -0, subnormal words; squares alone are too
# benign for an order mutant: their 1-ulp chunk differences are absorbed by the larger tree sums)
mkdir -p "$OUT/hh6"; python3 tools/hbm_static/su_pretree_bench.py "$OUT/hh6" > "$OUT/hh6/gen.log"
for mut in 0 1 1024; do (cd "$OUT/hh6" && "$OUT/obj$mut/vtb" $(cat plusargs.txt)) > "$OUT/hh6.mut$mut.log" 2>&1 || true
 echo "== hh6 order witness mut$mut: $(grep -E '^(PASS|FAIL)' "$OUT/hh6.mut$mut.log")"; done
rm -rf "$OUT"/obj* "$OUT"/*/stim.mem
