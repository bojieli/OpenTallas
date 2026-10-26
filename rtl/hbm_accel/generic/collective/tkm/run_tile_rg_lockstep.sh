#!/usr/bin/env bash
# HBM-C 2026-10-17: TKM e86 row-group tile vs generic CDUP tile lockstep (Verilator --timing).
# PASS = MUT0 PASS and MUT1 (clk_r2 skewed 3 of 10 ns) FAIL.  usage: run_tile_rg_lockstep.sh OUT [NCYC]
set -u
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$ROOT"
OUT=$(realpath -m "${1:?out}"); NCYC=${2:-4000}; mkdir -p "$OUT"; rc=0
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C=rtl/hbm_accel/generic/collective/tkm
for m in 0 1; do
  "$V" --binary --timing -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
    --top-module tb_hgi_coll_tkm_tile_rg_lockstep -GMUT=$m -GNCYC=$NCYC -Mdir "$OUT/obj$m" \
    "$C/tb_hgi_coll_tkm_tile_rg_lockstep.sv" "$C/ot_hgi_coll_tkm.sv" > "$OUT/build$m.log" 2>&1 || { tail -20 "$OUT/build$m.log"; exit 2; }
  "$OUT/obj$m/Vtb_hgi_coll_tkm_tile_rg_lockstep" > "$OUT/run$m.log" 2>&1
  r=$(grep "^TKM_RG_LOCKSTEP MUT$m cycles" "$OUT/run$m.log" | tail -1); echo "$r"; grep -m3 "MISMATCH\|VACUOUS\|Error" "$OUT/run$m.log"
  if [ $m -eq 0 ]; then case "$r" in *PASS) ;; *) rc=1;; esac; else case "$r" in *FAIL) ;; *) rc=1;; esac; fi
done
sha256sum "$C/tb_hgi_coll_tkm_tile_rg_lockstep.sv" "$C/ot_hgi_coll_tkm.sv" "$0" > "$OUT/sources.sha256"
[ $rc -eq 0 ] && echo "TKM_RG_LOCKSTEP_BENCH PASS" || echo "TKM_RG_LOCKSTEP_BENCH FAIL"
exit $rc
