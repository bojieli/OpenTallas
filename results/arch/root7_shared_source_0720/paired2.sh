#!/bin/bash
set -eu
R=$PWD
mkdir paired2
for side in base cand; do
 cp -a /srv/opentallas-scratch/claude/root5-shared-source-1020/base "paired2/$side"
 tar xf current.tar -C "paired2/$side"
done
(cd paired2/cand; git apply --binary "$R/candidate.patch")
export PYTHONPATH=/srv/opentallas-scratch/claude/root5-shared-source-1020/pylib
for side in base cand; do
 (cd "paired2/$side/tools/ref_tile"; set +e; python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' tests/test_ot_rst_copies.py tests/test_balanced_reset_landing.py tests/test_reset_landing.py tests/test_source_native_reset_landing.py > "$R/${side}_focused2.log" 2>&1; echo $? > "$R/${side}_focused2.rc") &
done
wait
cat base_focused2.rc cand_focused2.rc
tail -15 base_focused2.log
tail -15 cand_focused2.log
