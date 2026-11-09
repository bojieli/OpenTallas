#!/bin/bash
# build the 4 variants in parallel, then MUTK 0..7 x SEED 1,2 x NEP 240 per variant
cd "$(dirname "$0")"
for v in "unguarded 0" "unguarded 1" "guarded 0" "guarded 1"; do ./run.sh $v +NEP=2 > /dev/null 2>&1 & done; wait
for v in "unguarded 0" "unguarded 1" "guarded 0" "guarded 1"; do
  ( for k in 0 1 2 3 4 5 6 7; do for s in 1 2; do ./run.sh $v +MUTK=$k +SEED=$s +NEP=240; done; done > final_${v// /_kr}.out ) &
done; wait
grep -hE "\] (kr|mismatch|PASS|FAIL)" final_*.out
