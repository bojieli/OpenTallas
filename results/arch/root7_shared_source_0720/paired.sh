#!/bin/bash
set -eu
R=$PWD
mkdir paired
for side in base cand; do
 cp -a /srv/opentallas-scratch/claude/root5-shared-source-1020/base "paired/$side"
 tar xf current.tar -C "paired/$side"
done
(cd paired/cand; git apply --binary "$R/candidate.patch")
export PYTHONPATH=/srv/opentallas-scratch/claude/root5-shared-source-1020/pylib
for side in base cand; do
 (cd "paired/$side/tools/ref_tile"; set +e; python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' tests/test_ot_rst_copies.py tests/test_balanced_reset_landing.py tests/test_reset_landing.py tests/test_source_native_reset.py > "$R/${side}_focused.log" 2>&1; echo $? > "$R/${side}_focused.rc") &
done
wait
cat base_focused.rc cand_focused.rc
tail -15 base_focused.log
tail -15 cand_focused.log
