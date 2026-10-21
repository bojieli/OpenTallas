#!/bin/bash
# Closure-loop case adapter: one source-bound build shared by cases, mutants return failure after their expected witness.
set -euo pipefail
BASE=$(readlink -f "$1"); CASE=$2
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
mkdir -p "$BASE"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
(
flock -x 9
if [ ! -f "$BASE/src/source_manifest.json" ]; then python3 "$ROOT/results/arch/codex_ctlm_safe10_1021/prepare_bench.py" "$BASE/src"; fi
cd "$BASE/src"
OBJ=obj; EXTRA=()
if [ "$CASE" = tok_drop17 ]; then OBJ=obj_drop17; EXTRA=(-GCALMUT=35); fi
if [ ! -x "$OBJ/Vtb_qfd_tt_ctlm_dv_lpf_lp" ]; then
 verilator --binary --timing -j 8 -Wno-fatal --top-module tb_qfd_tt_ctlm_dv_lpf_lp "${EXTRA[@]}" -f safe10.f --Mdir "$OBJ" > "$OBJ.build.log" 2>&1 || { tail -n 30 "$OBJ.build.log"; exit 3; }
fi
) 9>"$BASE/build.lock"
cd "$BASE/src"
OBJ=obj; IMAGE=calr10
case "$CASE" in tok_rel) ;; tok_norel) IMAGE=calr10n;; tok_abs1) IMAGE=calr10a;; tok_drop17) OBJ=obj_drop17;; *) echo BAD_CASE;exit 3;; esac
"$OBJ/Vtb_qfd_tt_ctlm_dv_lpf_lp" +MUT=0 +SEED=5 +CALRDIR=2 +CALR_ROM_DIR="$IMAGE" > "$CASE.log" 2>&1 || true
cat "$CASE.log"
if [ "$CASE" = tok_rel ]; then grep -q 'LP_LOCKSTEP PASS.*calrdir=2' "$CASE.log"; grep -q 'TLOAD_PRODUCER PASS' "$CASE.log";exit 0;fi
if grep -q 'TLOAD_PRODUCER FAIL' "$CASE.log"; then exit 1;fi
exit 0
