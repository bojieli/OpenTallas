#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p out
for mode in 0 1; do
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_stream -GSTATIC="$mode" --Mdir "out/obj$mode" rtl/test/qwen_dv/static_stream/tb_stream.sv rtl/qwen_dv/qfd_dv_stream{,_packer}.sv > "out/build$mode.log" 2>&1
 "out/obj$mode/Vtb_stream" > "out/run$mode.log" 2>&1
done
for mut in 2 21 22; do
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_stream -GMUT="$mut" --Mdir "out/mut$mut" rtl/test/qwen_dv/static_stream/tb_stream.sv rtl/qwen_dv/qfd_dv_stream{,_packer}.sv > "out/build_mut$mut.log" 2>&1
 set +e
 "out/mut$mut/Vtb_stream" > "out/run_mut$mut.log" 2>&1
 code=$?
 set -e
 test "$code" -ne 0
 grep -E 'PACKER_INTERNAL_MISMATCH|STREAM_EQ_MISMATCH' "out/run_mut$mut.log"
done
