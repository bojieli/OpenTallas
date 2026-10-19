#!/bin/bash
# HBM-NEXT-ATT4 A1 (2026-10-19): bench matrix of the PV merge variants (shared = PRIMARY ot_hnx_att4_smerge, flop = per-lane
# flop-stack fallback), run on ONE fleet host from the synced source root (cwd):
#   ot-run --mem 160 --threads 96 --dir <src> -- bash tools/hbm_next/att4_a1_matrix.sh <out dir> [name ...]
# Each run: tools/hbm_next/att4_bench.py (Verilator 5.050), own work dir, verdict line in <out>/<name>.log, JSON in <out>/<name>.json.
set -u
OUT=$1; shift
mkdir -p "$OUT"
export VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
declare -A R=(
  [sh_s00]="--variant shared --sigma 0.0 --p1"
  [sh_s03]="--variant shared --sigma 0.3 --p1"
  [sh_s10]="--variant shared --sigma 1.0"
  [sh_sdj]="--variant shared --sigma -1 --p1"
  [sh_smut1]="--variant shared --sigma 0.3 --smut 1 --only p0,p1,p2,p3"
  [sh_smut2]="--variant shared --sigma 0.3 --smut 2 --only p0,p1,p2,p3"
  [sh_smut3]="--variant shared --sigma 0.3 --smut 3 --only p0,p1,p2,p3"
  [sh_smut4]="--variant shared --sigma 0.3 --smut 4 --only p0,p1,p2,p3"
  [sh_k500]="--variant shared --sigma 0.3 --topk 500 --p1"
  [sh_k490]="--variant shared --sigma 0.3 --topk 490 --p1"
  [sh_k486]="--variant shared --sigma 0.0 --topk 486 --p1"
  [sh_smut4k]="--variant shared --sigma 0.3 --topk 500 --smut 4 --only p17,p18,p19"
  [fl_k500]="--variant flop --sigma 0.3 --topk 500 --p1"
  [fl_k490]="--variant flop --sigma 0.3 --topk 490"
  [fl_k486]="--variant flop --sigma 0.0 --topk 486"
  [fl_s00]="--variant flop --sigma 0.0 --p1"
  [fl_s03]="--variant flop --sigma 0.3 --p1"
  [fl_s10]="--variant flop --sigma 1.0"
  [fl_sdj]="--variant flop --sigma -1 --p1"
  [fl_pvmut1]="--variant flop --sigma 0.3 --pvmut 1 --only p0,p1,p2,p3"
  [fl_pvmut2]="--variant flop --sigma 0.3 --pvmut 2 --only p0,p1,p2,p3"
  [fl_pvmut5]="--variant flop --sigma 0.3 --pvmut 5 --only p0,p1,p2,p3"
  # step 3 (2026-10-19): publication path of the shared tile (ot_hnx_att4_spvm, PUBLISH 1) -> tools/hbm_next/att4_pub_bench.py
  [pub_m0]="--mut 0"
  [pub_s2]="--mut 0 --seed 2027 --rounds 36"
  [pub_m1]="--mut 1"
  [pub_m2]="--mut 2"
  [pub_m3]="--mut 3"
  [pub_m4]="--mut 4"
  [pub_m5]="--mut 5"
)
NAMES=("$@"); [ ${#NAMES[@]} -eq 0 ] && NAMES=("${!R[@]}")
P=${A1_PAR:-2}                       # concurrent runs (each Verilator build peaks ~7 GB)
run1() { n=$1; [ -s "$OUT/$n.json" ] && return 0
  case $n in
    pub_*) python3 tools/hbm_next/att4_pub_bench.py run --work "$OUT/w_$n" --out "$OUT/$n.json" ${R[$n]} > "$OUT/$n.log" 2>&1 ;;
    *) python3 tools/hbm_next/att4_bench.py run --work "$OUT/w_$n" --out "$OUT/$n.json" --jobs 8 ${R[$n]} > "$OUT/$n.log" 2>&1 ;;
  esac
  echo "rc=$?" >> "$OUT/$n.log"; }
i=0
for n in "${NAMES[@]}"; do
  run1 "$n" &
  i=$((i + 1)); [ $((i % P)) -eq 0 ] && wait
done
wait
grep -h "HNX_ATT4" "$OUT"/*.log | cut -c1-200
