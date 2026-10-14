#!/bin/bash
set -e
VLT="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$VLT" --binary --timing -j 1 -Wno-fatal --top-module tb_qwen_numeric_queue_service --Mdir obj ot_qwen_numeric_output_queue.sv tb_qwen_numeric_queue_service.sv > build.log 2>&1
./obj/Vtb_qwen_numeric_queue_service > run.log
cat run.log
