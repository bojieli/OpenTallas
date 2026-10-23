#!/usr/bin/env bash
# HBM-P5-RTLA: TP192 TKM core-split twin gate, trace form (the in-tb pinned reference of run_tp192_static_p.sh needed
# >290 GB in one verilation).  STEP=build_<v> builds one model (v = pin|p1|p0|mut); STEP=sim runs all cases:
# golden O/R vectors + timeline in every model (syn_sel/syn_cand/rank128_zeros), offline lock-step twin PIPE1 vs pinned
# at +2 edges (all 3 cases), PIPE0 vs pinned at +0 (syn_sel); mutant MUTP 1 must FAIL (golden and lock-step).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);cd "$ROOT"
OUT=$(realpath -m "${1:?out}");STEP=${2:-all};mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective
src=("$C/tkm/tkm_tp192_e86_hier.vlt" "$C/tkm/tb_hgi_coll_tkm_static_pt.sv" "$C/tkm/ot_hgi_coll_tkm_static_p.sv" "$C/tkm/ot_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm.sv" "$C/tkm/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
vec(){ [ -f "$OUT/vec/cases.json" ] || OPENBLAS_NUM_THREADS=1 python3 tools/hgi_coll_tkm_tp192_vectors.py --out "$OUT/vec" > "$OUT/vectors.log"; }
build(){ # name PINNED PIPE MUTP
 # e86 wrapper = hier block (tkm_tp192_e86_hier.vlt); two make steps (TKM-3 10-18: _hier.mk's two-target rule races under -j)
 { "$V" --cc --exe --main --timing --hierarchical -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module tb_hgi_coll_tkm_static_pt -Mdir "$OUT/obj_$1" -GTP=192 -GKMAX=2048 -GPINNED=$2 -GPIPE=$3 -GMUTP=$4 "${src[@]}" &&
   make -C "$OUT/obj_$1" -f Vtb_hgi_coll_tkm_static_pt_hier.mk -j1 hier_verilation &&
   make -C "$OUT/obj_$1" -f Vtb_hgi_coll_tkm_static_pt_hier.mk -j${JOBS:-8} hier_build; } > "$OUT/build_$1.log" 2>&1
 echo "BUILT $1"; }
case "$STEP" in
 vec) vec;sha256sum "${src[@]}" "$C/tkm/tkm_trace_lockstep.py" "$C/tkm/run_tp192_static_pt.sh" tools/hgi_coll_tkm_tp192_vectors.py tools/hgi_coll_tkm_vectors.py > "$OUT/sources.sha256";;
 build_pin) build pin 1 0 0;; build_p1) build p1 0 1 0;; build_p0) build p0 0 0 0;; build_mut) build mut 0 1 1;;
 sim)
  vec;L=$C/tkm/tkm_trace_lockstep.py
  for tc in syn_sel syn_cand rank128_zeros;do
   for m in pin p1;do "$OUT/obj_$m/Vtb_hgi_coll_tkm_static_pt" +DIR="$OUT/vec/$tc" +ROTATE=128 +TRACE="$OUT/tr_${m}_$tc.txt" > "$OUT/${m}_$tc.log" 2>&1 & done;wait
   grep 'TKM_STATIC_PT PASS' "$OUT/pin_$tc.log";grep 'TKM_STATIC_PT PASS' "$OUT/p1_$tc.log"
   python3 $L "$OUT/tr_pin_$tc.txt" "$OUT/tr_p1_$tc.txt" 2 | tee "$OUT/lockstep_p1_$tc.log"
  done
  "$OUT/obj_p0/Vtb_hgi_coll_tkm_static_pt" +DIR="$OUT/vec/syn_sel" +ROTATE=128 +TRACE="$OUT/tr_p0_syn_sel.txt" > "$OUT/p0_syn_sel.log" 2>&1
  grep 'TKM_STATIC_PT PASS' "$OUT/p0_syn_sel.log"
  python3 $L "$OUT/tr_pin_syn_sel.txt" "$OUT/tr_p0_syn_sel.txt" 0 | tee "$OUT/lockstep_p0_syn_sel.log"
  set +e
  "$OUT/obj_mut/Vtb_hgi_coll_tkm_static_pt" +DIR="$OUT/vec/syn_sel" +ROTATE=128 +TRACE="$OUT/tr_mut_syn_sel.txt" > "$OUT/mut_syn_sel.log" 2>&1;rc=$?
  python3 $L "$OUT/tr_pin_syn_sel.txt" "$OUT/tr_mut_syn_sel.txt" 2 > "$OUT/lockstep_mut_syn_sel.log" 2>&1;lrc=$?
  set -e
  [ "$rc" != 0 ] && grep -q 'TKM_STATIC_PT FAIL' "$OUT/mut_syn_sel.log" && [ "$lrc" != 0 ] && echo "MUTANT MUTP1 FAILS as required: $(grep -m1 'TKM_STATIC_PT FAIL' "$OUT/mut_syn_sel.log") | $(head -1 "$OUT/lockstep_mut_syn_sel.log")"
  echo TKM_TP192_STATIC_PT_GATE_PASS;;
 *) echo "STEP vec|build_pin|build_p1|build_p0|build_mut|sim";exit 2;;
esac
