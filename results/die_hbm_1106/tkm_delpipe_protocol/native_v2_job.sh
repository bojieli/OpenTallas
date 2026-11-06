#!/bin/bash
set -eu
cd "$(dirname "$0")"
export OBJCACHE= CCACHE_DISABLE=1
/usr/bin/time -v /home/ubuntu/.local/opentallas-tools/bin/verilator --binary -O1 -CFLAGS -O1 --output-split 20000 -j 4 -Wno-fatal -Wno-lint -Wno-style -DOT_TKM_DEL_PIPE1 --x-assign 0 --x-initial 0 --top-module tb_delpipe --Mdir obj_modes tb_native_modes.sv gold.sv delpipe_v2.sv sram.v > build_modes.log 2>&1
for mode in 0 1 2; do
 ./obj_modes/Vtb_delpipe +mode=$mode > mode_$mode.log 2>&1
 grep SUMMARY mode_$mode.log
done
