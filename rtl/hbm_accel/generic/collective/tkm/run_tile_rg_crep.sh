#!/usr/bin/env bash
# L2H-IDX e86s 2026-10-19: e86 CREP 1 (kept per-slice one-hot control copies) vs CREP 0 lockstep (Verilator 5.050 --timing).
# PASS = MUT0 PASS and MUT1 (CMUT 1: one slice holds instead of shifting) FAIL.  usage: run_tile_rg_crep.sh OUT [NCYC]
# One case: run_tile_rg_crep.sh OUT NCYC M  (M = 0 or 1) prints that case's TKM_RG_CREP line only.
set -u
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$ROOT"
OUT=$(realpath -m "${1:?out}"); NCYC=${2:-4000}; MS=${3:-"0 1"}; mkdir -p "$OUT"; rc=0
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective/tkm
for m in $MS; do
  "$V" --binary --timing -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
    --top-module tb_hgi_coll_tkm_tile_rg_crep -GMUT=$m -GNCYC=$NCYC -Mdir "$OUT/obj$m" \
    "$C/tb_hgi_coll_tkm_tile_rg_crep.sv" "$C/ot_hgi_coll_tkm.sv" > "$OUT/build$m.log" 2>&1 || { tail -20 "$OUT/build$m.log"; exit 2; }
  "$OUT/obj$m/Vtb_hgi_coll_tkm_tile_rg_crep" > "$OUT/run$m.log" 2>&1
  r=$(grep "^TKM_RG_CREP MUT$m cycles" "$OUT/run$m.log" | tail -1); echo "$r"; grep -m3 "MISMATCH\|VACUOUS\|Error" "$OUT/run$m.log"
  if [ $m -eq 0 ]; then case "$r" in *PASS) ;; *) rc=1;; esac; else case "$r" in *FAIL) ;; *) rc=1;; esac; fi
  case "$r" in *PASS) raw=0;; *) raw=1;; esac
done
# single-case form (job benches): exit with that case's own verdict (a mutant FAIL exits 1)
if [ $# -ge 3 ]; then sha256sum "$C/tb_hgi_coll_tkm_tile_rg_crep.sv" "$C/ot_hgi_coll_tkm.sv" "$0" > "$OUT/sources.sha256"; exit $raw; fi
sha256sum "$C/tb_hgi_coll_tkm_tile_rg_crep.sv" "$C/ot_hgi_coll_tkm.sv" "$0" > "$OUT/sources.sha256"
[ $rc -eq 0 ] && echo "TKM_RG_CREP_BENCH PASS" || echo "TKM_RG_CREP_BENCH FAIL"
exit $rc
