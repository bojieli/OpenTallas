#!/usr/bin/env bash
# S81-GUNIT whole model: ot_hdc_sinkhorn_fs vs ot_hdc_sinkhorn equivalence bench (Verilator).  usage: run_sinkhorn_fs_eq.sh
# [workdir] [cases] [mut] [mutq4]  (mut 0 mutq4 0 = positive, prints SKF PASS; mut 1 = stage-early mutant and mutq4 1 =
# corrupted Q4 range predicate, must print SKF FAIL).
# Reads: rtl/hdc/v41/ot_hdc_sinkhorn.sv ot_hdc_sinkhorn_fs.sv ot_hdc_skf_predecode.sv ot_hdc_sk_arith.sv
# ot_hdc_sk_recip_rom.sv, this dir's tb_sinkhorn_fs_eq.{sv,cpp}.
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
T=${1:-$(mktemp -d)}; N=${2:-200}; M=${3:-0}; Q=${4:-0}; mkdir -p "$T"
( cd "$T" && verilator --cc --exe --build -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DMUT=$M -DMUTQ4=$Q \
    --top-module tb_sinkhorn_fs_eq -Mdir "obj$M$Q" "$H/ot_hdc_sinkhorn.sv" "$H/ot_hdc_sinkhorn_fs.sv" "$H/ot_hdc_skf_predecode.sv" \
    "$H/ot_hdc_sk_arith.sv" "$H/ot_hdc_sk_recip_rom.sv" "$H/test/tb_sinkhorn_fs_eq.sv" "$H/test/tb_sinkhorn_fs_eq.cpp" \
    -CFLAGS -O1 > "build$M$Q.log" 2>&1 ) \
  || { echo "MUT=$M MUTQ4=$Q: SKF FAIL build"; tail -20 "$T/build$M$Q.log"; exit 2; }
out=$(cd "$T" && "./obj$M$Q/Vtb_sinkhorn_fs_eq" +N=$N +SEED=19 | grep -E '^(SKP|ERR)' | sed 's/^SKP/SKF/')
echo "$out" | sed "s/^/MUT=$M MUTQ4=$Q: /"
echo "$out" | grep -q '^SKF PASS'
