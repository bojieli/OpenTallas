#!/bin/bash
# 3 builds in parallel, then MUTK 0 and 3 x NEP 120 each (KR 1)
cd "$(dirname "$0")"
V="noprime prime mut"
for v in $V; do ./runbf.sh $v +NEP=2 > /dev/null 2>&1 & done; wait
for v in $V; do ( for k in 0 3; do ./runbf.sh $v +MUTK=$k +SEED=1 +NEP=120; done > final_$v.out ) & done; wait
{ echo "# irg PRIME banded-flat (bf, KR 1) bench $(date -u +%FT%TZ) $(hostname) src: $(tr -s ' ' < src/SHA256SUMS | tr '\n' ';')"
  grep -hE "\] (D |kr|mismatch|fail_open|out_diff|PASS|FAIL|SIM_RC)" final_*.out; } > summary.log
grep -hE "\] (PASS|FAIL|SIM_RC)" final_*.out
