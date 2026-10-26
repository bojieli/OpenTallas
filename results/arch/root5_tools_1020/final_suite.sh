#!/bin/bash
set -u
R=$PWD
mkdir final
cp -a grt/. final/
(cd final && git apply --binary ../final.patch) || exit 3
export PYTHONPATH="$R/pylib"
(cd final/tools/ref_tile && python3 -m pytest -p no:cacheprovider -q -o addopts="" tests/test_native_census.py tests/test_ktree_native_scope.py tests/test_pin_hook_after_flops.py tests/test_trial_route_completion.py tests/test_cts_dependency.py > "$R/final_focused.log" 2>&1); echo $? > final_focused.rc
(cd final/tools/ref_tile && python3 -m pytest -p no:cacheprovider -q -rfE -o addopts="" --continue-on-collection-errors . > "$R/final_ref_tile.log" 2>&1); echo $? > final_ref_tile.rc
