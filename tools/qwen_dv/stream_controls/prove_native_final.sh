#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
yosys -Q -T -p 'read_json native_final/candidate.json; write_verilog native_final/qfd_dv_stream_controls.v; stat -liberty mapped/combined.lib' > native_final/emit.log 2>&1
python3 tools/qwen_dv/stream_controls/build_native_bench.py
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_stream --Mdir native_final/obj native_final/tb_controls.sv native_final/qfd_dv_stream_controls.v candidate/models.v rtl/qwen_dv/qfd_dv_stream.sv > native_final/build.log 2>&1
for mut in 0 1 2 3 4; do
 set +e
 native_final/obj/Vtb_stream +MUT=$mut > native_final/run$mut.log 2>&1
 code=$?
 set -e
 if [ "$mut" = 0 ]; then test "$code" = 0; grep 'STREAM_CONTROLS_EQ PASS' native_final/run$mut.log; else test "$code" != 0; grep -E 'STREAM_EQ_MISMATCH|STREAM_RESET_MISMATCH' native_final/run$mut.log; fi
done
