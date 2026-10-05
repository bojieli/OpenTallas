#!/bin/bash
set -eu
ulimit -t unlimited;ulimit -v unlimited;ulimit -f unlimited
J=/srv/opentallas-scratch/jobs/euclid-pcwb-frame-ds20-functional-r1
cd /srv/opentallas/repos/euclid-pcwb-frame-ds20-20261005
trap 'rc=$?; echo "$rc" > "$J/exit"' EXIT
git rev-parse HEAD > "$J/source.commit"
git show HEAD:tools/hbm_pcwb_parent_sources.py > "$J/original_source_helper.py"
python3 "$J/original_source_helper.py" --root "$PWD" --enable 1 --cmd-match-cut 1 > "$J/original_selection.json"
python3 "$J/original_source_helper.py" --root "$PWD" --format paths > "$J/sources.f"
printf '%s\n' rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_pcwb_owner_frame_ds20.sv rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_pcwb_prepaid_column_frame_ds20.sv rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_accel_pcwb_service_stack_frame_ds20.sv >> "$J/sources.f"
verilator --lint-only --timing -Wno-fatal --top-module ot_hbm_accel_pcwb_service_stack_frame_ds20 -GENABLE=0 -GFRAME_DS20=0 -f "$J/sources.f" > "$J/default-lint.log" 2>&1
verilator --lint-only --timing -Wno-fatal --top-module ot_hbm_accel_pcwb_service_stack_frame_ds20 -GENABLE=1 -GFRAME_DS20=1 -GCMD_MATCH_CUT=1 -f "$J/sources.f" > "$J/enabled-lint.log" 2>&1
if grep -qE '%Error|%Warning-UNOPTFLAT|%Warning-LATCH.*frame_ds20' "$J/enabled-lint.log"; then exit 2;fi
verilator --binary --timing -Wno-fatal -j 4 --Mdir "$J/obj" --top-module tb_prepaid_frame_ds20 \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb_command_match.sv \
 rtl/hbm_accel/integration/ot_hbm_pcwb_ca_slots.sv \
 rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_pcwb_owner_frame_ds20.sv \
 rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_pcwb_prepaid_column_frame_ds20.sv \
 results/rtl/hbm_pcwb_frame_ds20_20261005/tb_prepaid_frame_ds20.sv > "$J/build.log" 2>&1
"$J/obj/Vtb_prepaid_frame_ds20" > "$J/runtime.log" 2>&1
