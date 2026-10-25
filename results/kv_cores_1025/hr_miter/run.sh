#!/bin/bash
# KV-CORE-RTL/HR miters: $1 = worktree, run in the current dir
set -u
WT=$1; V=$HOME/.local/opentallas-tools/bin/verilator
AF=$WT/rtl/link/ot_link_afifo.sv; CC=$WT/rtl/physical/ot_qwen_die_cdc_ch.sv
CCF="$CC $WT/rtl/physical/ot_qwen_async_fifo_w.sv $WT/rtl/lib/ot_reset_sync.sv"
run() { # name top files... -- extra args
  local n=$1; shift; local top=$1; shift
  rm -rf obj_$n; mkdir -p obj_$n
  $V --binary -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module $top -Mdir obj_$n -o sim "$@" > obj_$n/build.log 2>&1 || { echo "$n BUILD FAIL"; tail -5 obj_$n/build.log; return; }
  ./obj_$n/sim +verilator+seed+1 > $n.log 2>&1; echo "$n rc=$? :: $(grep -E 'MITER|LATENCY|STREAM' $n.log | tr '\n' ' ')"
  rm -rf obj_$n
}
for s in "514 4" "289 4" "256 4" "64 4"; do set -- $s
  run afifo_W$1 tb_afifo tb_afifo.sv $AF -GW=$1 -GAW=$2
done
run afifo_W514_MUT tb_afifo tb_afifo.sv $AF -GW=514 -GAW=4 +define+OT_LINK_AFIFO_MUT_SAMECLK
run samefifo_rsel2 tb_samefifo tb_samefifo.sv $CC -GRSEL2=1
run samefifo_rsel0 tb_samefifo tb_samefifo.sv $CC -GRSEL2=0
run samefifo_rsel2_MUT tb_samefifo tb_samefifo.sv $CC -GRSEL2=1 +define+OT_QWEN_SAMEFIFO_MUT
run cdcch_lat tb_cdcch_lat tb_cdcch_lat.sv +define+SYNTHESIS $CCF $WT/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1_bb.v
