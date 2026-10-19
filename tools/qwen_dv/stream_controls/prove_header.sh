#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p header_composition
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_stream --Mdir header_composition/obj rtl/test/qwen_dv/stream_controls/tb_header_compose.sv rtl/test/qwen_dv/stream_controls/header_sources/*.sv native_final/qfd_dv_stream_controls_retained.v candidate/models.v rtl/qwen_dv/qfd_dv_stream.sv > header_composition/build.log 2>&1
for phase in -80 0 80;do
 header_composition/obj/Vtb_stream +MUT=0 +PHASE=$phase > header_composition/pos${phase}.log 2>&1
 grep 'STREAM_HEADER_NATIVE_COMPOSE PASS' header_composition/pos${phase}.log
done
for mut in 1 2 3 4 5 7;do
 set +e
 header_composition/obj/Vtb_stream +MUT=$mut +PHASE=0 > header_composition/mut${mut}.log 2>&1
 code=$?
 set -e
 test "$code" != 0
 grep -E 'STREAM_EQ_MISMATCH|STREAM_RESET_MISMATCH|HEADER_CAPTURE_MISMATCH' header_composition/mut${mut}.log
done
for phase in -80 80;do
 set +e
 header_composition/obj/Vtb_stream +MUT=5 +PHASE=$phase > header_composition/mut5_phase${phase}.log 2>&1
 code=$?
 set -e
 test "$code" != 0
 grep 'STREAM_EQ_MISMATCH' header_composition/mut5_phase${phase}.log
done
