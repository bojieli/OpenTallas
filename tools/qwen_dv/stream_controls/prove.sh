#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
yosys -Q -T -p 'read_json candidate/candidate.json; write_verilog -noattr candidate/qfd_dv_stream_controls.v' > candidate/emit_verilog.log 2>&1
yosys -Q -T -p 'read_liberty -ignore_miss_func mapped/combined.lib; write_verilog -noattr candidate/models.v' > candidate/models.log 2>&1
python3 tools/qwen_dv/stream_controls/build_bench.py
for mut in 0 1 2 3; do
 verilator --binary --timing -j 2 -Wno-fatal --top-module tb_stream -GMUT=$mut --Mdir candidate/obj$mut candidate/tb_controls.sv candidate/qfd_dv_stream_controls.v candidate/models.v rtl/qwen_dv/qfd_dv_stream.sv > candidate/build$mut.log 2>&1
 set +e
 candidate/obj$mut/Vtb_stream > candidate/run$mut.log 2>&1
 code=$?
 set -e
 if [ "$mut" = 0 ]; then test "$code" = 0; grep 'STREAM_CONTROLS_EQ PASS' candidate/run$mut.log; else test "$code" != 0; grep -E 'STREAM_EQ_MISMATCH|STREAM_RESET_MISMATCH' candidate/run$mut.log; fi
done
