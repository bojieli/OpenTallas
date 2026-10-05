#!/bin/bash
set -eu
ulimit -t unlimited;ulimit -v unlimited;ulimit -f unlimited
J=/srv/opentallas-scratch/jobs/euclid-ds-pcwb-parent-lint-r2
cd /srv/opentallas/repos/euclid-ds-pcwb-parent-lint-r2-20261005
trap 'rc=$?; echo "$rc" > "$J/exit"' EXIT
git rev-parse HEAD > "$J/source.commit"
python3 tools/hbm_pcwb_parent_sources.py --enable 1 --cmd-match-cut 1 > "$J/selection.json"
python3 tools/hbm_pcwb_parent_sources.py --enable 1 --cmd-match-cut 1 --format paths > "$J/sources.f"
verilator --lint-only --timing -Wno-fatal --top-module ot_hbm_accel_pcwb_service_stack -GENABLE=1 -GCMD_MATCH_CUT=1 -f "$J/sources.f" > "$J/lint.log" 2>&1
if grep -qE '%Error|%Warning-UNOPTFLAT|%Warning-LATCH.*ot_hbm_accel_pcwb_service_stack.sv|%Warning-LATCH.*ot_hbm_pcwb_prepaid_column.sv' "$J/lint.log"; then exit 2;fi
