#!/bin/bash
# HBM-NEXT-P3-UNITS (2026-10-19, owner P3 decision 0le): ATT4 bench matrix at P = 3 query lanes (shared merge = production
# A1 variant), run on ONE fleet host from a git-archive source bundle (cwd):
#   ot-run --mem 96 --threads 32 --dir <src> -- bash tools/hbm_next/att4_p3_matrix.sh <out dir> [name ...]
# Same benches as tools/hbm_next/att4_a1_matrix.sh (Verilator 5.050), with --nl 3; nl4_* = the generic-NL regression at 4.
set -u
OUT=$1; shift
mkdir -p "$OUT"
export VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
declare -A R=(
  [sh_s00]="--nl 3 --variant shared --sigma 0.0 --p1"
  [sh_s03]="--nl 3 --variant shared --sigma 0.3 --p1"
  [sh_s10]="--nl 3 --variant shared --sigma 1.0"
  [sh_sdj]="--nl 3 --variant shared --sigma -1 --p1"
  [sh_k500]="--nl 3 --variant shared --sigma 0.3 --topk 500 --p1"
  [sh_k490]="--nl 3 --variant shared --sigma 0.3 --topk 490 --p1"
  [sh_k486]="--nl 3 --variant shared --sigma 0.0 --topk 486 --p1"
  [sh_smut6]="--nl 3 --variant shared --sigma 0.3 --smut 6 --only p0,p1,p2,p3"
  [sh_smut1]="--nl 3 --variant shared --sigma 0.3 --smut 1 --only p0,p1,p2,p3"
  [sh_smut2]="--nl 3 --variant shared --sigma 0.3 --smut 2 --only p0,p1,p2,p3"
  [sh_smut3]="--nl 3 --variant shared --sigma 0.3 --smut 3 --only p0,p1,p2,p3"
  [sh_smut4k]="--nl 3 --variant shared --sigma 0.3 --topk 500 --smut 4 --only p17,p18,p19"
  [sh_imut1]="--nl 3 --variant shared --sigma 0.3 --imut 1 --only q4,p4,q10,p10"
  [sh_imut2]="--nl 3 --variant shared --sigma 0.3 --imut 2 --only q4,p4,q10,p10"
  [sh_imut3]="--nl 3 --variant shared --sigma 0.3 --imut 3 --only q4,p4,q10,p10"
  [sh_imut4]="--nl 3 --variant shared --sigma 0.3 --imut 4 --only q4,p4,q10,p10"
  [nl4_s03]="--nl 4 --variant shared --sigma 0.3"
  [pub_m0]="--nl 3 --mut 0"
  [pub_s2]="--nl 3 --mut 0 --seed 2027 --rounds 36"
  [pub_m1]="--nl 3 --mut 1"
  [pub_m2]="--nl 3 --mut 2"
  [pub_m3]="--nl 3 --mut 3"
  [pub_m4]="--nl 3 --mut 4"
  [pub_m5]="--nl 3 --mut 5"
  [sched3]="stress --nl 3 --lv 3 --trials 20000"
)
NAMES=("$@"); [ ${#NAMES[@]} -eq 0 ] && NAMES=("${!R[@]}")
P=${A1_PAR:-4}                       # concurrent runs (each Verilator build peaks ~7 GB)
run1() { n=$1; [ -s "$OUT/$n.json" ] && return 0
  case $n in
    sched*) python3 tools/hbm_next/att4_smerge_sched.py ${R[$n]} --out "$OUT/$n.json" > "$OUT/$n.log" 2>&1 ;;
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
grep -h "HNX_ATT4\|faults" "$OUT"/*.log | cut -c1-240
