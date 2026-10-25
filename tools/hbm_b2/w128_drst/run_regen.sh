#!/bin/bash
# HBM-W128 2026-10-25: regenerate the four W128 bank pair cuts with the fixed HC leaf (.DRST(ADRST) on the multiplier),
# rerun the same-cycle composition miters + write-enable mutants and the reset census.
set -uo pipefail
cd "$(dirname "$0")"
declare -A TOP=([plain]=ot_hbm_hc_bankq_static [first]=ot_hbm_hc_bankq0_static [feed]=ot_hbm_hc_bankq_ft_static [term]=ot_hbm_hc_bankq_term_static)
declare -A MST=([plain]=ot_hbm_hc_bank128_pair_core [first]=ot_hbm_hc_bank128_pair_first_core [feed]=ot_hbm_hc_bank128_pair_core [term]=ot_hbm_hc_bank128_pair_core)
for v in plain first feed term; do
 ( cd $v && bash run_all.sh > run_all.out 2>&1 && echo "$v regen rc=0" || echo "$v regen FAIL"
   python3 ../hc128_pair_miter.py --top ${TOP[$v]} --root . > miter.out 2>&1; echo "$v miter rc=$?"
   python3 ../hc128_reset_census.py pair_compact/compact128.json --top ${MST[$v]} --out reset_census.json > census.out 2>&1; echo "$v census rc=$?"
 ) 2>&1 | tee $v.status &
done
wait
cat */miter/result.json | grep -E '"verdict"|proven' ; cat */census.out
