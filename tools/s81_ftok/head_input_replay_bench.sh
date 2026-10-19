#!/bin/bash
set -eu
O=$(realpath -m "$1");mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -Wno-fatal -Wno-lint -O1 --top-module tb_s81_head_input_replay --Mdir "$O/obj" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/dsrom_sys/s81_native_head_connect/ot_s81_head_input_replay.sv rtl/dsrom_sys/s81_native_head_connect/test/tb_s81_head_input_replay.sv > "$O/build.log" 2>&1
for m in 0 1 2 3 4;do
 "$O/obj/Vtb_s81_head_input_replay" +MUT=$m > "$O/m$m.log" 2>&1
 cat "$O/m$m.log"
 if [ "$m" = 0 ];then grep -q 'HEAD_INPUT_REPLAY PASS' "$O/m$m.log";else grep -q 'HEAD_INPUT_REPLAY FAIL' "$O/m$m.log";fi
done
