#!/usr/bin/env bash
# TP=192 TKM negative (expect FAIL): the TIE_W_MUT=1 build (192-rank tie id truncated to 7 bits) on rank128_zeros must
# report MISMATCH R / TKM_STATIC FAIL.  Prints the run log; exits with the simulator status.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);cd "$ROOT"
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT"
OPENBLAS_NUM_THREADS=1 python3 tools/hgi_coll_tkm_tp192_vectors.py --out "$OUT/vec" > "$OUT/vectors.log" || exit 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective
# TKM-3 10-18: hierarchical verilation is run as two make steps.  Verilator's _hier.mk has an explicit two-target rule
# (<blk>.sv <blk>.mk) that make -j runs TWICE in parallel; with the e86 hier block both copies wrote the same dir and
# the e86 lib failed 'PCH invalid / __pch.h.fast missing' (2 of 2 runs).  Step 1 verilates without --build (Verilator runs the hier verilation serially; the -j1 make is a no-op check),
# step 2 builds -j8.  Checked KMAX=128 on ot-epyc5 (2 e86 stubs, binary built).
vbuild(){ local obj=$1;shift;"$V" --cc --exe --main --timing --hierarchical -O2 "$@" -Mdir "$obj" &&
 make -C "$obj" -f Vtb_hgi_coll_tkm_static_hier.mk -j1 hier_verilation && make -C "$obj" -f Vtb_hgi_coll_tkm_static_hier.mk -j8 hier_build; }
src=("$C/tkm/tkm_tp192_hier.vlt" "$C/tkm/tb_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm.sv" "$C/tkm/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
# HIERWRAP=1 (HBMc/TILES4 10-22): parameter-free e86 hier wrappers (tkm_tp192_hierwrap.vlt); default build unchanged
HW=();if [ "${HIERWRAP:-0}" = 1 ];then src[0]="$C/tkm/tkm_tp192_hierwrap.vlt";src+=("$C/tkm/ot_hgi_coll_tkm_e86_hw.sv");HW=(-DOT_TKM_HIERWRAP);fi
vbuild "$OUT/obj1" -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT "${HW[@]}" --top-module tb_hgi_coll_tkm_static -GTP=192 -GKMAX=2048 -GFAN32=${FAN32:-0} -GRT=${RT:-0} -GTIE_W_MUT=1 "${src[@]}" > "$OUT/build1.log" 2>&1 || { tail -20 "$OUT/build1.log"; exit 2; }
"$OUT/obj1/Vtb_hgi_coll_tkm_static" +DIR="$OUT/vec/rank128_zeros" +ROTATE=128 > "$OUT/mut.log" 2>&1; rc=$?
grep -E 'MISMATCH R|TKM_STATIC' "$OUT/mut.log" | head -5
exit $rc
