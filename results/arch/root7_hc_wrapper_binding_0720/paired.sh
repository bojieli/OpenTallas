#!/bin/bash
set -eu
R=$PWD
for side in base cand; do
 cp -a /srv/opentallas-scratch/claude/root5-shared-source-1020/base "$side"
 tar xf current.tar -C "$side"
 (cd "$side"; git unpack-objects < "$R/metadata.pack" >/dev/null)
done
(cd cand; git apply --binary "$R/candidate.patch")
tar xf newtests.tar -C cand
export PYTHONPATH=/srv/opentallas-scratch/claude/root5-shared-source-1020/pylib
cohort=(tests/test_source_binding.py tests/test_gate_binding_precise.py tests/test_gate_binding_consumed.py tests/test_gate_only_binding.py tests/test_staged_remeasurement.py tests/test_ruletag_classification.py tests/test_reset_landing.py tests/test_rc_ioref_balanced_reset_requirement.py tests/test_child_flop_basis_requirement.py tests/test_landed_root_spread.py tests/test_anchor_row_packing.py)
for side in base cand; do
 extra=(); if [ "$side" = cand ]; then extra=(tests/test_source_binding_wrapper_compat.py); fi
 (cd "$side/tools/ref_tile"; set +e; python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' "${cohort[@]}" "${extra[@]}" > "$R/${side}_focused.log" 2>&1; echo $? > "$R/${side}_focused.rc") &
done
wait
cat base_focused.rc cand_focused.rc
tail -18 base_focused.log
tail -18 cand_focused.log
python3 actual_replay.py
