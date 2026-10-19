#!/bin/bash
set -euo pipefail
cd run
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 4 -Wno-fatal -DOT_MEM_NO_INIT --top-module tb_qwen_witness_native32 -Mdir native32_obj native32_source.v ../src/rtl/test/qwen_dv/tb_qwen_witness_native32.sv > native32_build.log 2>&1
native32_obj/Vtb_qwen_witness_native32 "+IMAGE=$PWD/packed_sram.hex" > native32_port.log
grep WITNESS_NATIVE32_PASS native32_port.log
