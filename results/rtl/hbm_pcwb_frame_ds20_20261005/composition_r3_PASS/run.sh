#!/bin/bash
set -eu
ulimit -t unlimited; ulimit -v unlimited; ulimit -f unlimited
J=/srv/opentallas-scratch/jobs/euclid-ds20-cp-composition-r3
cd /srv/opentallas/repos/euclid-ds20-cp-composition-20261005
trap 'rc=$?; echo "$rc" > "$J/exit"' EXIT
git rev-parse HEAD > "$J/source.commit"
git status --porcelain > "$J/source.dirty"
test ! -s "$J/source.dirty"
git show HEAD:tools/hbm_pcwb_parent_sources.py > "$J/original_source_helper.py"
python3 "$J/original_source_helper.py" --root "$PWD" --format paths > "$J/sources.f"
printf '%s\n' rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_pcwb_owner_frame_ds20.sv rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_pcwb_prepaid_column_frame_ds20.sv rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_accel_pcwb_service_stack_frame_ds20.sv rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_accel_pcwb_service_stack_ds20_window.sv >> "$J/sources.f"
verilator --lint-only --timing -Wno-fatal --top-module ot_hbm_accel_pcwb_service_stack_ds20_window -GENABLE=1 -GCMD_MATCH_CUT=1 -f "$J/sources.f" > "$J/receiver-lint.log" 2>&1
verilator --binary --timing -Wno-fatal -j 4 --Mdir "$J/obj" --top-module tb_ds20_cp_service \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv \
 rtl/hbm_accel/integration/ot_ds_hbm_pcwb_owner_join.sv rtl/hbm_accel/service/ot_hbm_accel_dskv_wb.sv \
 rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb_command_match.sv rtl/hbm_accel/integration/ot_hbm_pcwb_ca_slots.sv \
 rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_pcwb_owner_frame_ds20.sv \
 rtl/hbm_accel/integration/frame_ds20_20261005/ot_hbm_pcwb_prepaid_column_frame_ds20.sv \
 results/rtl/hbm_pcwb_frame_ds20_20261005/tb_ds20_cp_service.sv > "$J/build.log" 2>&1
"$J/obj/Vtb_ds20_cp_service" > "$J/runtime.log" 2>&1
