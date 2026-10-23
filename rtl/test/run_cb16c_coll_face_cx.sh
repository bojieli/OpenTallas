#!/bin/bash
# CB16c-COLL 10-22: lockstep bench of the regional-split collective face vs the original face RTL (Verilator).
#   run_cb16c_coll_face_cx.sh OUTDIR PROFILE [MUT]
#   PROFILE s0 (HARD 1: PHY 350, R 0, PEER_R 5, L0 381) | p (HARD 2: PHY 20, R 5, PEER_R 5, L0 56)
#   MUT 0 pass (PHI 0/1 x PPH 0/2); 1 OT_CB16C_MUT_SWAP; 2 OT_CB16C_MUT_RXSKIP; 3 OT_CB16C_MUT_NOXR; 4 OT_CB16C_MUT_NOXT
# Prints "CB16C_COLL_FACE_CX ..." per case and "CB16C_COLL_BENCH PASS|FAIL MUT=<m>" (a mutant must FAIL).
set -u
OUT=${1:?outdir}; PROF=${2:?profile}; MUT=${3:-0}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
SRC=(rtl/test/tb_cb16c_coll_face_cx.sv rtl/test/tb_coll_static_face.sv
     rtl/physical/qwen_coll_cb16c_1022/qfd_coll_face_cx.sv rtl/physical/qwen_coll_cb16c_1022/qfd_coll_face_cx_body.sv
     rtl/physical/ot_qfd_coll_static_face.sv rtl/physical/ot_qfd_static_transport.sv
     rtl/rom/ot_coll_static_linkcal.sv rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv
     rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
     rtl/lib/ot_reset_sync.sv rtl/physical/qwen_coll_safe_1019/ot_coll_phy_land.sv
     physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
     physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
case $PROF in
  s0) G=(-GHARD=1 -GPHY=350 -GL0=381 -GR=0 -GPEER_R=5) ;;
  p)  G=(-GHARD=2 -GPHY=20 -GL0=56 -GR=5 -GPEER_R=5) ;;
  *) echo "bad profile $PROF"; exit 2 ;;
esac
DEF=(-DOT_COLL_REGIONAL -DOT_COLL_BANK_LOCAL); CASES="0:0 1:0 0:2 1:2"
case $MUT in
  0) ;;
  1) DEF+=(-DOT_CB16C_MUT_SWAP); CASES="0:0" ;;
  2) DEF+=(-DOT_CB16C_MUT_RXSKIP); CASES="0:0" ;;
  3) DEF+=(-DOT_CB16C_MUT_NOXR); CASES="0:0" ;;
  4) DEF+=(-DOT_CB16C_MUT_NOXT); CASES="0:0" ;;
  *) echo "bad MUT $MUT"; exit 2 ;;
esac
ok=1
for c in $CASES; do
  PHI=${c%%:*}; PPH=${c##*:}; tag="${PROF}_m${MUT}_phi${PHI}_pph${PPH}"
  (cd "$ROOT" && "${VERILATOR:-verilator}" --binary --timing -O1 -j ${VJOBS:-8} -Wno-fatal -Wno-lint -Wno-style \
      --top-module tb_cb16c_coll_face_cx "${G[@]}" -GPHI=$PHI -GPPH=$PPH -Mdir "$OUT/obj_$tag" -o sim \
      "${DEF[@]}" "${SRC[@]}") > "$OUT/build_$tag.log" 2>&1 || { tail -30 "$OUT/build_$tag.log"; echo "$tag BUILD FAIL"; ok=0; continue; }
  "$OUT/obj_$tag/sim" > "$OUT/run_$tag.log" 2>&1
  grep -E "^(ERR|CB16C_)" "$OUT/run_$tag.log" | head -12 | sed "s/^/$tag /"
  grep -q "^CB16C_COLL_FACE_CX PASS$" "$OUT/run_$tag.log" || ok=0
  rm -rf "$OUT/obj_$tag"
done
if [ $ok = 1 ]; then echo "CB16C_COLL_BENCH PASS MUT=$MUT PROFILE=$PROF"; exit 0; else echo "CB16C_COLL_BENCH FAIL MUT=$MUT PROFILE=$PROF"; exit 1; fi
