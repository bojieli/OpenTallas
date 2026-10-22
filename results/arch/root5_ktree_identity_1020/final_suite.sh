#!/bin/bash
set -eu
R=$PWD
cp -a --reflink=auto cand finalcand
cp final-native_census.py finalcand/tools/ref_tile/native_census.py
cp test_final.py finalcand/tools/ref_tile/tests/test_ktree_buffer_identity.py
export PYTHONPATH="$R/pylib"
set +e
(cd finalcand/tools/ref_tile && python3 -m pytest -p no:cacheprovider -q -o addopts="" tests/test_native_census.py tests/test_ktree_native_scope.py tests/test_ktree_buffer_identity.py > "$R/final_focused.log" 2>&1); echo $? > final_focused.rc
(cd finalcand/tools/ref_tile && python3 -m pytest -p no:cacheprovider -q -rfE -o addopts="" --continue-on-collection-errors . > "$R/final_ref_tile.log" 2>&1); echo $? > final_ref_tile.rc
