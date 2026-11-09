#!/bin/bash
# build the 6 variants in parallel, then MUTK 0 (real design) and 3 (chunk release 3 edges late: stale for D <= 5)
# x NEP 120 (D 1..12 x 10 epochs) per variant / KR; summary.log = the counter lines of every run
cd "$(dirname "$0")"
V="noprime_0 noprime_1 prime_0 prime_1 mut_0 mut_1"
for v in $V; do ./run.sh ${v%_*} ${v#*_} +NEP=2 > /dev/null 2>&1 & done; wait
for v in $V; do
  ( for k in 0 3; do ./run.sh ${v%_*} ${v#*_} +MUTK=$k +SEED=1 +NEP=120; done > final_${v%_*}_kr${v#*_}.out ) &
done; wait
{ echo "# irg rg3 PRIME bench $(date -u +%FT%TZ) $(git rev-parse --short HEAD) (+ working tree)"
  grep -hE "\] (D |kr|mismatch|fail_open|out_diff|PASS|FAIL)" final_*.out; } > summary.log
grep -hE "\] (PASS|FAIL)" final_*.out
