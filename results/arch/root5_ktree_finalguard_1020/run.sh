#!/bin/bash
set -eu
R=$PWD
if [ ! -d source ]; then cp -a ../root5-shared-source-1020/base source; fi
tar xf guard.tar -C source
export PYTHONPATH="$R/../root5-shared-source-1020/pylib"
(
 cd source/tools/ref_tile
 set +e
 python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' tests/test_native_census.py tests/test_ktree_native_scope.py tests/test_ktree_buffer_identity.py tests/test_ktree_identity_receipt_shape.py > "$R/focused.log" 2>&1
 echo $? > "$R/focused.rc"
) &
focus=$!
set +e
python3 actual.py > actual.log 2>&1
echo $? > actual.rc
wait "$focus"
cat focused.log actual.log
test "$(cat focused.rc)" = 0 && test "$(cat actual.rc)" = 0
