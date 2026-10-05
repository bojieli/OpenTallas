#!/bin/bash
set -eu
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
J=/srv/opentallas-scratch/jobs/euclid-ds-pcwb-parent-functional-r1
R=/srv/opentallas/repos/euclid-ds-pcwb-parent-20261005
cd "$R"
trap 'rc=$?; echo "$rc" > "$J/exit"; date -u > "$J/finished"' EXIT
git rev-parse HEAD > "$J/source.commit"
python3 tools/hbm_pcwb_parent_sources.py --enable 1 --cmd-match-cut 1 > "$J/selection.json"
python3 tools/hbm_pcwb_parent_sources.py --format paths > "$J/sources.f"
for pair in '0 0' '1 0' '1 1'; do
 read -r en cmd <<< "$pair"
 verilator --lint-only --timing -Wno-fatal --top-module ot_hbm_accel_pcwb_service_stack -GENABLE="$en" -GCMD_MATCH_CUT="$cmd" -f "$J/sources.f" > "$J/lint-$en-$cmd.log" 2>&1
done
verilator --binary --timing -Wno-fatal -j 4 --Mdir "$J/obj" --top-module tb_prepaid_join \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv \
 rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb_command_match.sv \
 rtl/hbm_accel/integration/ot_hbm_pcwb_ca_slots.sv \
 rtl/hbm_accel/integration/ot_hbm_pcwb_prepaid_column.sv \
 results/rtl/hbm_pcwb_parent_implementation_20261005/tb_prepaid_join.sv > "$J/build.log" 2>&1
"$J/obj/Vtb_prepaid_join" > "$J/runtime.log" 2>&1
