#!/bin/bash
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
run=$1
mut=$2
mkdir -p "$run"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vl" --version > "$run/tool.txt"
common=(rtl/qwen_split/qfd_native59_dv_service.sv rtl/qwen_split/qfd_native59_qbank.sv rtl/qwen_split/qfd_native59_svc.sv rtl/qwen_split/qfd_native59_split_flat.sv rtl/qwen_split/qfd_native59_q_export_control.sv rtl/qwen_split/qfd_native59_command_context.sv rtl/qwen_split/qfd_native59_static_service.sv rtl/qwen_split/qfd_native59_record_endpoint.sv rtl/qwen_split/qfd_kvn_static_transport.sv rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v)
cd "$root"
"$vl" --cc --exe --build -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_n59_boundary_pair -GRECV_MUT="$mut" -Mdir "$run/obj" "${common[@]}" rtl/test/qwen_split/tb_n59_boundary_pair.sv "$root/rtl/test/qwen_split/tb_n59_boundary_pair_main.cpp" > "$run/build.log" 2>&1 || exit 2
"$run/obj/Vtb_n59_boundary_pair" > "$run/run.log" 2>&1
rc=$?
sha256sum "${common[@]}" rtl/test/qwen_split/tb_n59_boundary_pair.sv > "$run/source.sha256"
if [ "$mut" = 0 ]; then
 test "$rc" = 0 && grep -q '^N59PAIR_PASS' "$run/run.log" || exit 1
 echo N59PAIR_BASE_PASS
else
 test "$rc" != 0 && grep -q '^N59PAIR_FAIL' "$run/run.log" || exit 1
 echo "N59PAIR_MUTANT_REJECTED $mut"
fi
