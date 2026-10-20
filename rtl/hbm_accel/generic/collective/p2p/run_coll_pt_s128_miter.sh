#!/usr/bin/env bash
# HBM-COLLFJ2 10-19: random miter of the SAFE fj programme target (ot_hgi_coll_static_program_target_s128, in
# ot_hgi_coll_safe_leaves.sv) vs the closed ot_hgi_coll_static_program_target #(ROWS 128).  FLEET ONLY (Verilator 5.050):
#   bash rtl/hbm_accel/generic/collective/p2p/run_coll_pt_s128_miter.sh OUT [pass|lastale|ldhnofwd]
# pass: PT_S128_MITER PASS (exit 0).  Mutants (job benches expect fail): exit 1 + 'PT_S128_MUTANT <m> REJECTED' when the
# miter FAILS on the mutant, exit 0 + SURVIVED otherwise.
set -u
OUT=$(realpath -m "${1:?OUT}"); MODE=${2:-pass}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
"$V" --version | tee "$OUT/verilator.version"
p=rtl/hbm_accel/generic/collective/p2p
# the q3 SAFE parent child list (safe_leaves references the other hard leaves; the 128x64 SRAM model is in it)
SRC="$(python3 -c "import json;s=json.load(open('results/arch/landed_parent_1018/collq/spec_q3_ars.json'));print(' '.join(s['child_sources']))") $p/tb_hgi_coll_pt_s128_miter.sv"
case $MODE in pass) D="";; lastale) D="+define+OT_PT_MUT_LA_STALE";; ldhnofwd) D="+define+OT_PT_MUT_LDH_NOFWD";; *) echo "bad mode"; exit 2;; esac
sha256sum $SRC > "$OUT/sources.sha256"
"$V" --binary -j ${VL_JOBS:-8} -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTITOP $D +define+PT_EPISODES=${PT_EPISODES:-3000} \
  --top-module tb_hgi_coll_pt_s128_miter $SRC -Mdir "$OUT/obj_$MODE" > "$OUT/$MODE.build.log" 2>&1 || { tail -30 "$OUT/$MODE.build.log"; echo "PT_S128_BUILD FAIL"; exit 3; }
"$OUT/obj_$MODE/Vtb_hgi_coll_pt_s128_miter" +seed=${SEED:-1019} > "$OUT/$MODE.log" 2>&1
rm -rf "$OUT/obj_$MODE"
grep -E '^PT_S128' "$OUT/$MODE.log" | head -12
if [ "$MODE" = pass ]; then grep -q '^PT_S128_MITER PASS' "$OUT/$MODE.log" && { echo "PT_S128_EXIT 0"; exit 0; }; echo "PT_S128_EXIT 1"; exit 1; fi
if grep -q '^PT_S128_MITER FAIL' "$OUT/$MODE.log"; then echo "PT_S128_MUTANT $MODE REJECTED"; exit 1; fi
echo "PT_S128_MUTANT $MODE SURVIVED"; exit 0
