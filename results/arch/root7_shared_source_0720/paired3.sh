#!/bin/bash
set -eu
R=$PWD
mkdir paired3
for side in base cand; do
 cp -a /srv/opentallas-scratch/claude/root5-shared-source-1020/base "paired3/$side"
 tar xf current.tar -C "paired3/$side"
done
(cd paired3/cand; git apply --binary "$R/candidate3.patch")
export PYTHONPATH=/srv/opentallas-scratch/claude/root5-shared-source-1020/pylib
for side in base cand; do
 (cd "paired3/$side/tools/ref_tile"; set +e; python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' tests/test_ot_rst_copies.py tests/test_balanced_reset_landing.py tests/test_reset_landing.py tests/test_source_native_reset_landing.py > "$R/${side}_focused3.log" 2>&1; echo $? > "$R/${side}_focused3.rc") &
done
wait
cat base_focused3.rc cand_focused3.rc
tail -15 base_focused3.log
tail -15 cand_focused3.log

for name in ot_kvpc5_and2 ot_kvpc6_and2; do
 yosys -Q -T -p "read_verilog $name.v; hierarchy -top $name; proc; write_json $name.json" > "$name.yosys.log" 2>&1
done
python3 coupon.py
