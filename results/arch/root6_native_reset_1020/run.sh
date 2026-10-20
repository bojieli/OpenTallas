#!/bin/bash
set -eu
R=$PWD
cp -a ../root5-shared-source-1020/base source
tar xf current.tar -C source
tar xf candidate.tar -C source
export PYTHONPATH="$R/../root5-shared-source-1020/pylib"
cd source/tools/ref_tile
set +e
python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' tests/test_source_native_reset_landing.py tests/test_reset_landing.py tests/test_balanced_reset_landing.py tests/test_textbook_execution.py tests/test_rc_ioref_balanced_reset_requirement.py > "$R/focused.log" 2>&1
rc=$?
echo "$rc" > "$R/focused.rc"
cat "$R/focused.log"
exit "$rc"
