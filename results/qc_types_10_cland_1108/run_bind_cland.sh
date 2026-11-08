#!/bin/bash
# QC-TYPES-10/CLAND: strict native bind of plan_qc53v4w (UNCHANGED, e5dc7eacb745) with the CLAND tool patch
# (landing_collector.raw_reset site identity + check_local_resets; ring_taps density -> reset_tree._taps), on the
# bind_v4w producer tools (src_d95ec) and the same asbuilt (asbuilt_reach.json). Out dir starts as a copy of bind_v4w
# (elab outputs reused, as run_bind_v4w.sh did).
set -u
W=/srv/opentallas-scratch2/claude/qct10/cland; F=$W/farm; cd $F
P=physical/die_plan/qwen_compute/plan_of_record/plan_qc53v4w.json
RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
date
python3 -B tools/die_plan/bind.py bind $P --out $W/bind_cland --strict --asbuilt $RT/asbuilt_reach.json > $W/bind.log 2>&1; echo "BIND rc $?" >> $W/bind.log
date
