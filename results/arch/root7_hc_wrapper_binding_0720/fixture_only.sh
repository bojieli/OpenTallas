#!/bin/bash
set -eu
R=$PWD
export PYTHONPATH=/srv/opentallas-scratch/claude/root5-shared-source-1020/pylib
for side in base cand; do
 mkdir -p "$side/physical/qwen_die_masters"
 cp io_flop_at_pins.tcl "$side/physical/qwen_die_masters/"
 (cd "$side/tools/ref_tile"; python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' tests/test_anchor_row_packing.py::SourceClosure::test_row_packer_is_consumed_with_the_anchoring_hook > "$R/${side}_fixture_only.log" 2>&1)
 cat "${side}_fixture_only.log"
done
