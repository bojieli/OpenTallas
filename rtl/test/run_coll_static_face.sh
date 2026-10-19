#!/bin/bash
# Q-DIE11-COLL 2026-10-18: qfd_coll_static_face production-shape bench (rtl/test/tb_coll_static_face.sv), iverilog.
#   run_coll_static_face.sh OUTDIR [MUT]   MUT 0 = pass (PHI 0 and PHI 1), 1 = RX CDC read 1 early (OT_LCAL_MUT_RX_EARLY),
#                                          2 = CDC read pipe 1 short (OT_STATIC_MUT_LATENCY), 3 = PHY 1 link cycle long (XS=1),
#                                          4 = codec bank write-through hit select corrupted (OT_QKD_REPLAY_HIT_MUT)
# env TOK_REG (default 1) = the face TOK_REG parameter; HARD=1 adds +define OT_QFD_FACE_HARD (closed bank leaf form)
# Prints "MUT=<m> PHI=<p> ..." per case and a final "COLL_STATIC_FACE_BENCH PASS|FAIL MUT=<m>".
set -u
OUT=${1:?outdir}; MUT=${2:-0}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
SRC=(rtl/test/tb_coll_static_face.sv rtl/physical/ot_qfd_coll_static_face.sv rtl/physical/ot_qfd_static_transport.sv
     rtl/rom/ot_coll_static_linkcal.sv rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv
     rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
     rtl/lib/ot_reset_sync.sv
     physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
     physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
DEF=(); XS=0; PHIS="0 1"; TOK=${TOK_REG:-1}
case $MUT in
  0) ;;
  1) DEF=(-DOT_LCAL_MUT_RX_EARLY); PHIS=0 ;;
  2) DEF=(-DOT_STATIC_MUT_LATENCY); PHIS=0 ;;
  3) XS=1; PHIS=0 ;;
  4) DEF=(-DOT_QKD_REPLAY_HIT_MUT); PHIS=0 ;;
  *) echo "bad MUT $MUT"; exit 2 ;;
esac
[ "${HARD:-0}" = 1 ] && DEF+=(-DOT_QFD_FACE_HARD)
ok=1
for PHI in $PHIS; do
  exe="$OUT/face_m${MUT}_phi${PHI}.vvp"
  (cd "$ROOT" && iverilog -g2012 -s tb_coll_static_face -P tb_coll_static_face.XS=$XS -P tb_coll_static_face.PHI=$PHI -P tb_coll_static_face.TOK_REG=$TOK \
      "${DEF[@]}" -o "$exe" "${SRC[@]}") > "$OUT/build_m${MUT}_phi${PHI}.log" 2>&1 || { cat "$OUT/build_m${MUT}_phi${PHI}.log"; echo "MUT=$MUT PHI=$PHI BUILD FAIL"; ok=0; continue; }
  vvp -n "$exe" > "$OUT/run_m${MUT}_phi${PHI}.log" 2>&1
  grep -E "^(ERR|COLL_)" "$OUT/run_m${MUT}_phi${PHI}.log" | sed "s/^/MUT=$MUT PHI=$PHI /"
  grep -q "^COLL_STATIC_FACE PASS$" "$OUT/run_m${MUT}_phi${PHI}.log" || ok=0
done
if [ $ok = 1 ]; then echo "COLL_STATIC_FACE_BENCH PASS MUT=$MUT"; exit 0; else echo "COLL_STATIC_FACE_BENCH FAIL MUT=$MUT"; exit 1; fi
