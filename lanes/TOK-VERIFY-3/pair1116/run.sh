#!/bin/bash
set -euo pipefail
ulimit -c 0
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$(dirname "$0")"
/usr/bin/time -f 'elapsed %e maxrss_kb %M' -o build.time verilator --binary --timing -Wno-fatal -j 4 --top-module tb --Mdir obj tb.sv gold.sv selected_bc4_rom64.sv ot_qwen_d2d_cal_seq_bc4.sv ot_qwen_d2d_cal_seq_rom64_core.sv ot_rom_64x32_m2.v > build.log 2>&1
/usr/bin/time -f 'elapsed %e maxrss_kb %M' -o run.time ./obj/Vtb > run.log 2>&1
grep -q BC4_EPOCH_PASS run.log
tail -9 run.log
