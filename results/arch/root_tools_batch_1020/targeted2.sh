#!/bin/bash
set -u
R=$(pwd);export PYTHONPATH="$R/pylib"
cp -an cand3/rtl/. cand/rtl/
(cd cand/tools/closure_loop; python3 -m pytest -q -o addopts="" test_rule_enforcement.py -k EveryRoot > "$R/targeted2_roots.log" 2>&1); a=$?
(cd cand/tools/closure_loop; python3 -m pytest -q -o addopts="" test_ck_insertion_clock_source.py test_gate_rule_guard.py > "$R/targeted2_clock.log" 2>&1); b=$?
(cd cand/tools/ref_tile; python3 -m pytest -q -o addopts="" test_cdc_batch_constraints.py test_cdc_seam_constraints.py tests/test_ruletag_classification.py > "$R/targeted2_cdc.log" 2>&1); c=$?
for cohort in roots clock cdc; do tail -4 "targeted2_${cohort}.log"; done
printf 'TARGETED_RC %s %s %s\n' "$a" "$b" "$c"
exit $((a+b+c))
