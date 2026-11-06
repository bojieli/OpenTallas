#!/bin/bash
# DIE-HEAD-71: beat_tx HOLD_REAL proofs (yosys).  Usage: beat_tx_hold_real_eq.sh MAIN_beat_link.sv BRANCH_beat_link.sv NEW_OUTDIR
# (1) HOLD_REAL 0 (default) == main at 6 parameter points (register-matched equiv_induct);
# (2) HOLD_REAL 1 == main, IDLE_ZERO 1, at the two hd_ctl points (k-induction with the invariant below).
set -u; D=$(cd "$(dirname "$0")" && pwd); OLD=$1; NEW=$2; OUT=$3
if [ -e "$OUT" ]; then echo "refusing existing output $OUT" >&2; exit 2; fi
bash "$D/beat_tx_hold_real_eq.d/eqdef.sh" "$OLD" "$NEW" "$OUT/default" && bash "$D/beat_tx_hold_real_eq.d/eqhr.sh" "$OLD" "$NEW" "$OUT/hold_real"
r=$?; echo "BEAT_TX_HOLD_REAL_EQ rc=$r"; exit $r
