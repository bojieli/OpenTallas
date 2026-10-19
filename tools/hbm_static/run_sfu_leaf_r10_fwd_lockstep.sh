#!/bin/bash
# HBM-NATIVE 2026-10-17: leaf lockstep r10 (dedicated chain-forward flops) vs the closed r10 leaf RTL (ref0).
# Usage: OUT=dir [SEED=n] [N=edges] [EQ_MUT=fwd] tools/hbm_static/run_sfu_leaf_r10_fwd_lockstep.sh
# r10n2 (KH-NATIVE3): chain out = closed RTL + 1 edge. Positive: exit 0 iff PASS. Mutant fwd (r10n forward from the pin, 1 edge): exit 0 iff the bench FAILS.
set -euo pipefail
mkdir -p "$OUT"
src=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_store_stripe_leaf_r10.sv rtl/test/hbm_accel/generic/ref/ot_hgi_sfu_store_stripe_leaf_r10_ref0.sv
 physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v rtl/test/hbm_accel/generic/tb_sfu_leaf_r10_fwd_lockstep.sv)
defs=()
case "${EQ_MUT:-}" in fwd) defs+=(-DOT_SFU_LEAF10_MUT_FWD);; "") ;; *) echo bad EQ_MUT >&2; exit 2;; esac
sha256sum "${src[@]}" "$0" > "$OUT/sources.sha256"
iverilog -g2012 -o "$OUT/sim" "${defs[@]}" -s tb_sfu_leaf_r10_fwd_lockstep "${src[@]}" > "$OUT/build.log" 2>&1
set +e
vvp -n "$OUT/sim" +SEED="${SEED:-12345}" +N="${N:-60000}" 2>&1 | grep -v '\$finish called' > "$OUT/run.log"
set -e
grep -h "SFU_LEAF_FWD" "$OUT/run.log" | tail -n 6
if [ -z "${EQ_MUT:-}" ]; then
  grep -q '^SFU_LEAF_FWD_LOCKSTEP PASS' "$OUT/run.log" && echo "SFU_LEAF_FWD_GATE POSITIVE PASS" && exit 0
  echo "SFU_LEAF_FWD_GATE POSITIVE FAIL"; exit 1
else
  grep -q '^SFU_LEAF_FWD_LOCKSTEP FAIL' "$OUT/run.log" && grep -q '^SFU_LEAF_FWD_MISMATCH' "$OUT/run.log" && \
    echo "SFU_LEAF_FWD_GATE MUTANT ${EQ_MUT} REJECTED (expected)" && exit 0
  echo "SFU_LEAF_FWD_GATE MUTANT ${EQ_MUT} ESCAPED"; exit 1
fi
