#!/bin/bash
# S-DIE-KCOPY 2026-10-16 reproduction (run on the fleet: ot-run --mem 4 --threads 1 ...):
#   python3 tools/s81/prove_dedupe_pad.py --kcopy --map results/arch/tile_dedupe_1015/s81_pad_map_kcopy_1016.json --out OUT [--mutant swap|droppad]
#   bash OUT/run.sh     (iverilog -g2012; positive prints KCOPY_EXACT PASS, a mutant ends KCOPY_FAIL / $fatal)
set -euo pipefail
R=$(git rev-parse --show-toplevel)
for mu in none swap droppad; do
  O=${TMPDIR:-/tmp}/kcopy_$mu; rm -rf $O
  python3 $R/tools/s81/prove_dedupe_pad.py --kcopy --map results/arch/tile_dedupe_1015/s81_pad_map_kcopy_1016.json --out $O --mutant $mu
  if bash $O/run.sh > $O/sim.log 2>&1; then r=PASS; else r=FAIL; fi
  grep -m1 'KCOPY_EXACT\|KCOPY_MISMATCH' $O/sim.log; echo "$mu $r"
done
