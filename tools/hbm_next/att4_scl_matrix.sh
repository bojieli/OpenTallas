#!/bin/bash
# HNEXT.ATT4 cluster-leaf successor (claude/hnx-att4-leaf-1020): lockstep + golden publication matrix of the two-leaf
# cluster ot_hnx_att4_scl vs the flat ot_hnx_att4_spvm (tools/hbm_next/att4_pub_bench.py --top scl), Verilator 5.050,
# safe reset defines (as the kits).  mut 0 must PASS; 2 / 6 (core: result into lane^1 ring / storage skew) and
# 7 / 8 / 9 (seam: S->N lane-2 seam late / S reset run long / wrong publication half) must FAIL.
# usage: att4_scl_matrix.sh OUTDIR [ROUNDS]     (run from the repo root; writes OUTDIR/scl_m<k>.{json,log})
set -u
OUT=${1:?outdir}; R=${2:-24}
mkdir -p "$OUT"
export HNX_ATT_SAFE_RESET=1
export VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
run() {
  m=$1
  python3 tools/hbm_next/att4_pub_bench.py run --nl 3 --top scl --rounds "$R" --work "$OUT/w_m$m" \
     --out "$OUT/scl_m$m.json" --mut "$m" --seed "${SEED:-1019}" > "$OUT/scl_m$m.log" 2>&1
  echo "mut $m rc $?"
}
export -f run; export OUT R SEED
printf "%s\n" ${MUTS:-0 2 6 7 8 9} | xargs -P 6 -I{} bash -c 'run {}'
for m in ${MUTS:-0 2 6 7 8 9}; do echo "== m$m: $(grep -E '^(PASS|FAIL) HNX_ATT4_PUB' "$OUT/scl_m$m.log" | cut -c1-300)"; done
