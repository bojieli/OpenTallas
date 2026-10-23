#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);cd "$ROOT"
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT"
OPENBLAS_NUM_THREADS=1 python3 tools/hgi_coll_tkm_tp192_vectors.py --out "$OUT/vec" > "$OUT/vectors.log"
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
sha256sum "${src[@]}" tools/hgi_coll_tkm_tp192_vectors.py tools/hgi_coll_tkm_vectors.py > "$OUT/sources.sha256"
for mut in 0 1; do
 vbuild "$OUT/obj$mut" -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT "${HW[@]}" --top-module tb_hgi_coll_tkm_static -GTP=192 -GKMAX=2048 -GTIE_W_MUT=$mut "${src[@]}" > "$OUT/build$mut.log" 2>&1
 if [ "$mut" = 0 ];then
  for tc in syn_sel syn_cand rank128_zeros;do
   "$OUT/obj0/Vtb_hgi_coll_tkm_static" +DIR="$OUT/vec/$tc" +ROTATE=128 > "$OUT/$tc.log" 2>&1
   grep 'TKM_STATIC PASS' "$OUT/$tc.log"
  done
 else
  set +e
  "$OUT/obj1/Vtb_hgi_coll_tkm_static" +DIR="$OUT/vec/rank128_zeros" +ROTATE=128 > "$OUT/mut_tie_rank7.log" 2>&1
  rc=$?
  set -e
  [ "$rc" != 0 ] && grep -q 'MISMATCH R' "$OUT/mut_tie_rank7.log" && grep -q 'TKM_STATIC FAIL' "$OUT/mut_tie_rank7.log"
 fi
done
echo TKM_TP192_STATIC_GATE_PASS
