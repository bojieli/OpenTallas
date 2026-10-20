#!/bin/bash
# TOKSIM-HBM-su 10-19: ROW_NORM sum-of-squares spans on ot_hbm_su_reduce_static (the reducer of the bound
# ot_hbm_su_static_qcore), tools/hbm_static/su_reduce_tb.cpp checks every scalar's exact cycle + bit-exact value.
# Run from the source root.  usage: run_rms_reduce.sh OUT
set -euo pipefail
OUT=$(realpath -m "$1"); mkdir -p "$OUT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; "$VL" --version > "$OUT/verilator.txt"
src=(rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_reduce_static.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
sha256sum "${src[@]}" tools/hbm_static/su_reduce_tb.cpp tools/hbm_static/su_reduce_compile.py tools/hbm_static/toksim_su/sfu/rms_reduce_compile.py > "$OUT/sources.sha256"
"$VL" --cc --exe --build -j 4 -Wno-fatal --top-module ot_hbm_su_reduce_static --Mdir "$OUT/obj" "${src[@]}" "$(pwd)/tools/hbm_static/su_reduce_tb.cpp" > "$OUT/build.log" 2>&1 || { tail -20 "$OUT/build.log"; exit 1; }
for c in d4096 seg128_q2 seg128_k1; do
 python3 tools/hbm_static/toksim_su/sfu/rms_reduce_compile.py "$OUT/$c" $c > "$OUT/$c.compile.txt"
 set +e; "$OUT/obj/Vot_hbm_su_reduce_static" "$OUT/$c" > "$OUT/$c.log" 2>&1; echo "rc=$?" >> "$OUT/$c.log"; set -e
 # mutant witness: the 'phase' mutant of su_reduce_tb (scalar one cycle off) must FAIL
 set +e; "$OUT/obj/Vot_hbm_su_reduce_static" "$OUT/$c" phase > "$OUT/$c.mut_phase.log" 2>&1; echo "rc=$?" >> "$OUT/$c.mut_phase.log"; set -e
 echo "== $c"; cat "$OUT/$c.compile.txt"; cat "$OUT/$c.log"; tail -2 "$OUT/$c.mut_phase.log"
done
rm -rf "$OUT/obj"
