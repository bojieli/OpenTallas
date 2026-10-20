#!/bin/bash
set -u
R=$(pwd);export PYTHONPATH="$R/pylib"
(cd cand3/tools/closure_loop; python3 -m pytest -q -o addopts="" test_native_reach_reason.py test_closed_stands.py test_rule_enforcement.py test_gate_rule_guard.py -k 'not test_submit_side' > "$R/native_reach_shared.log" 2>&1); a=$?
(cd cand3/tools/ref_tile; python3 -m pytest -q -o addopts="" test_cdc_batch_constraints.py test_cdc_sync_constraints.py test_cdc_seam_constraints.py tests/test_reroute_scope.py > "$R/native_reach_cdc.log" 2>&1); b=$?
python3 actual_native_reach_check.py > actual_native_reach.log 2>&1; c=$?
tail -7 native_reach_shared.log; tail -7 native_reach_cdc.log; cat actual_native_reach.log
printf 'RESULTS %s %s %s\n' "$a" "$b" "$c"
exit $((a+b+c))
