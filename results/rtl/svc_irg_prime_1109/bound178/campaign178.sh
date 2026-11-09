#!/bin/bash
# 6 builds in parallel (noprime / prime / mut x the two bound readers), then MUTK 0 and 3 x NEP 120 each
cd "$(dirname "$0")"
V="noprime prime mut"; M="dsdv_idx_rg3 dsdv_idx_rg3_nq_native"
for v in $V; do for m in $M; do ./run178.sh $v $m +NEP=2 > /dev/null 2>&1 & done; done; wait
for v in $V; do for m in $M; do
  ( for k in 0 3; do ./run178.sh $v $m +MUTK=$k +SEED=1 +NEP=120; done > final_${v}_$m.out ) &
done; done; wait
{ echo "# irg PRIME bound-b178 bench $(date -u +%FT%TZ) $(hostname) src: $(cat src/SHA256SUMS | tr -s ' ' | tr '\n' ';')"
  grep -hE "\] (D |kr|mismatch|fail_open|out_diff|PASS|FAIL|SIM_RC)" final_*.out; } > summary.log
grep -hE "\] (PASS|FAIL|SIM_RC)" final_*.out
