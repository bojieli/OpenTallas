#!/bin/bash
# SFU-PS-FUND 2026-10-17: store-level lockstep r7c (closed) vs r10 (11 one-stripe spine leaves).
# Decision B (SFU-PS-3): r10 programme side = r7c + 1 edge (tb PSHIFT=1); EQ_MUT=noshift = combinational programme start (must fail).
# Relays (SFU-PS-4): IO side r7c + 1 (ISHIFT=1), programme side r7c + 3 (PSHIFT=3); EQ_MUT=rowskew = row R3 bypasses its launch relay.
# r10n2 (KH-NATIVE3): leaf chain hop 2 edges; EQ_MUT=depth1 = head keeps r10n 1-edge-per-hop strobe depths, fwd1 = leaf keeps the r10n pin forward.
# Usage: OUT=dir [MODE=0..4] [SEED=n] [EQ_MUT=flip|chain|noshift|rowskew] tools/hbm_static/run_sfu_store_r10_lockstep.sh
# Positive (no EQ_MUT): exit 0 iff SFU_STORE_R10_LOCKSTEP PASS. Mutant: exit 0 iff the bench FAILS (mutant rejected).
set -euo pipefail
mkdir -p "$OUT"
P=rtl/hbm_accel/generic/peers
src=($P/ot_hgi_sfu_programme_store_r7c.sv $P/ot_hgi_sfu_program_stripe_rc.sv $P/ot_hgi_sfu_calendar_paged_rc.sv $P/ot_hgi_sfu_io_calendar_rc.sv
 $P/ot_hgi_sfu_store_stripe_leaf_r10.sv $P/ot_hgi_sfu_programme_store_r10.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v
 rtl/test/hbm_accel/generic/tb_sfu_store_r10_lockstep.sv)
defs=()   # EQ_MUT=flip uses OT_SFU_PSTORE10_MUT_FLIP: r10 only (the r7c reference reads OT_SFU_PSTORE_MUT_FLIP)
case "${EQ_MUT:-}" in flip) defs+=(-DOT_SFU_PSTORE10_MUT_FLIP);; chain) defs+=(-DOT_SFU_PSTORE10_MUT_CHAIN);; noshift) defs+=(-DOT_SFU_PSTORE10B_MUT_NOSHIFT);; rowskew) defs+=(-DOT_SFU_PSTORE10C_MUT_ROWSKEW);; depth1) defs+=(-DOT_SFU_PSTORE10N2_MUT_DEPTH1);; fwd1) defs+=(-DOT_SFU_LEAF10_MUT_FWD);; "") ;; *) echo bad EQ_MUT >&2;exit 2;; esac
sha256sum "${src[@]}" "$0" > "$OUT/sources.sha256"
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary -O2 -j 8 -Wno-fatal -Wno-TIMESCALEMOD "${defs[@]}" --top-module tb_sfu_store_r10_lockstep --Mdir "$OUT/obj" "${src[@]}" > "$OUT/build.log" 2>&1
set +e
"$OUT/obj/Vtb_sfu_store_r10_lockstep" +MODE="${MODE:-0}" +SEED="${SEED:-1}" ${GAP:++GAP=$GAP} > "$OUT/run.log" 2>&1
rc=$?
set -e
grep -h "SFU_STORE_R10" "$OUT/run.log" || tail -n 5 "$OUT/run.log"
if [ -z "${EQ_MUT:-}" ];then
 [ "$rc" = 0 ] && grep -q 'SFU_STORE_R10_LOCKSTEP PASS' "$OUT/run.log" && echo "SFU_STORE_R10_GATE POSITIVE PASS mode=${MODE:-0}" && exit 0
 echo "SFU_STORE_R10_GATE POSITIVE FAIL rc=$rc";exit 1
else
 [ "$rc" != 0 ] && grep -q 'SFU_STORE_R10_LOCKSTEP FAIL\|SFU_STORE_R10_MISMATCH' "$OUT/run.log" && echo "SFU_STORE_R10_GATE MUTANT ${EQ_MUT} REJECTED (expected)" && exit 0
 echo "SFU_STORE_R10_GATE MUTANT ${EQ_MUT} ESCAPED rc=$rc";exit 1
fi
