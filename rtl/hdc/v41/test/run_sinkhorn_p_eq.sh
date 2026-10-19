#!/usr/bin/env bash
# S81-SAFE-FIX/GUNIT: ot_hdc_sinkhorn_p vs ot_hdc_sinkhorn equivalence bench (Verilator).  usage: run_sinkhorn_p_eq.sh
# [workdir] [cases] [mut]  (mut 0 = positive, prints SKP PASS; mut 1 = stage-early mutant, must print SKP FAIL).
# Reads: rtl/hdc/v41/ot_hdc_sinkhorn.sv ot_hdc_sinkhorn_p.sv ot_hdc_sk_arith.sv ot_hdc_sk_recip_rom.sv, this dir's tb.
set -u
H=$(cd "$(dirname "$0")/.." && pwd)
T=${1:-$(mktemp -d)}; N=${2:-200}; M=${3:-0}; mkdir -p "$T"
( cd "$T" && verilator --cc --exe --build -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DMUT=$M \
    --top-module tb_sinkhorn_p_eq -Mdir "obj$M" "$H/ot_hdc_sinkhorn.sv" "$H/ot_hdc_sinkhorn_p.sv" "$H/ot_hdc_sk_arith.sv" \
    "$H/ot_hdc_sk_recip_rom.sv" "$H/test/tb_sinkhorn_p_eq.sv" "$H/test/tb_sinkhorn_p_eq.cpp" -CFLAGS -O1 > "build$M.log" 2>&1 ) \
  || { echo "MUT=$M: SKP FAIL build"; tail -20 "$T/build$M.log"; exit 2; }
out=$(cd "$T" && "./obj$M/Vtb_sinkhorn_p_eq" +N=$N +SEED=19 | grep -E '^(SKP|ERR)')
echo "$out" | sed "s/^/MUT=$M: /"
echo "$out" | grep -q '^SKP PASS'
