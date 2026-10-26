#!/usr/bin/env bash
set -u
BASE=/srv/opentallas-scratch/claude/codex-cdc-liberty-1021
cd "$BASE/ve_review_repo_1619" || exit 2
export CL_REPO="$PWD" CL_STATE="$BASE/ve_state_1620" CL_REVIEW="$BASE/ve_review_1620"
python3 -m pytest -q tools/closure_loop --junitxml="$BASE/ve_baseline_1620.xml" > "$BASE/ve_baseline_1620.log" 2>&1
echo "$?" > "$BASE/ve_baseline_1620.rc"
git apply --no-index "$BASE/ve_final_minimal.patch" || exit 3
cp "$BASE/infra_eco_continuation.py" "$BASE/test_infra_eco_continuation.py" tools/closure_loop/
cp "$BASE/ve_f51_source_readset.json" tools/closure_loop/evidence/
python3 -m pytest -q tools/closure_loop --junitxml="$BASE/ve_candidate_1620.xml" > "$BASE/ve_candidate_1620.log" 2>&1
echo "$?" > "$BASE/ve_candidate_1620.rc"
