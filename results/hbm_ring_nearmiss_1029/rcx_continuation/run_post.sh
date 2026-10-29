#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-ring-nearmiss-1029
K="$D/kit_drt"
# Invoked only after the normal DRT/finish/abstract job has released this kit.
test -f "$K/run/results/asap7/hbc_ot_hfd_coll_q2_hard_v8g__ring_ag/base/6_final.odb"
cp "$D/post_helpers/clock_family.tcl" "$K/clock_family.tcl"
cp "$D/post_helpers/data_droop.py" "$K/data_droop.py"
cp "$D/post_helpers/core_io_reference.py" "$K/core_io_reference.py"
bash "$K/run_kit_hbm.sh" "$K" post 32 8 > "$D/post.log" 2>&1
