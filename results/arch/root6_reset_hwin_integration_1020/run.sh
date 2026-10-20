#!/bin/bash
set -eu
R=$PWD
cp -a ../root5-shared-source-1020/base source
tar xf current.tar -C source
export PYTHONPATH="$R/../root5-shared-source-1020/pylib"
cd source/tools/ref_tile
set +e
python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' tests/test_source_native_reset_landing.py test_planning_birth_budget.py test_measured_band_fill.py test_lattice_channel_fill.py test_ref_tile.py::Job test_ref_tile.py::PinRegs::test_plan_and_env tests/test_reset_landing.py tests/test_balanced_reset_landing.py tests/test_textbook_execution.py tests/test_rc_ioref_balanced_reset_requirement.py > "$R/combined.log" 2>&1
rc=$?
echo "$rc" > "$R/combined.rc"
cat "$R/combined.log"
exit "$rc"
