#!/bin/bash
set -u
R=$PWD
mkdir grt
cp -a cand/. grt/
(cd grt && git apply --binary ../grt.patch) || exit 3
export PYTHONPATH="$R/pylib"
(cd grt/tools/ref_tile && python3 -m pytest -p no:cacheprovider -q -o addopts="" tests/test_trial_route_completion.py tests/test_cts_dependency.py > "$R/grt_focused.log" 2>&1); echo $? > grt_focused.rc
(cd grt/tools/ref_tile && python3 -m pytest -p no:cacheprovider -q -rfE -o addopts="" --continue-on-collection-errors . > "$R/grt_ref_tile.log" 2>&1); echo $? > grt_ref_tile.rc
