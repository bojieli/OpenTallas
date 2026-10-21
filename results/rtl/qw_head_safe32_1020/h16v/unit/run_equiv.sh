#!/bin/bash
# repo root; yosys 0.68 (orfs asap7lock image) sequential equivalence of the h16v fixed-issue copies
set -u; O=${1:-/tmp/h16v_equiv}; mkdir -p $O
docker run --rm -v "$PWD:/src:ro" -v "$O:/out" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -s /src/results/rtl/qw_head_safe32_1020/h16v/unit/equiv_fixed_issue.ys > $O/equiv.log 2>&1; rc=$?
grep -E "Found [0-9]+ unproven|equivalent|Equivalence successfully|ERROR" $O/equiv.log | tail -5; echo "EQUIV rc=$rc"; exit $rc
