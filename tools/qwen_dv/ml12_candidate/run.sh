#!/bin/bash
set -euo pipefail
cd /
R=$(cd "$(dirname "$0")/../../.." && pwd)
O=$1; MODE=${2:-ml12}
mkdir -p "$O"
case "$MODE" in
 ml12) TOP=tb_ml12_sensitive; TB=tools/qwen_dv/ml12_candidate/tb_ml12_sensitive.sv;;
 ml8) TOP=tb_ml8_req4_sensitive; TB=tools/qwen_dv/ml12_candidate/tb_ml8_req4_sensitive.sv;;
 alignment7) TOP=tb_s8_memalign; TB=tools/qwen_dv/mif1309/tb_ml12_alignment7.sv;;
 *) exit 2;;
esac
cd "$R"
/home/ubuntu/.local/opentallas-tools/bin/verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --top-module "$TOP" -f tools/qwen_dv/ml12_candidate/sources_relative.f rtl/qwen_dv/qfd_dv_head_safe1.sv rtl/qwen_dv/qfd_dv_lane_h_ml12_candidate.sv tools/qwen_dv/ml12_candidate/ma7_guard_only_fixture.sv "$TB" -Mdir "$O/obj" > "$O/build.log" 2>&1
"$O/obj/V$TOP" > "$O/run.log" 2>&1
