#!/bin/bash
# TOK-QK/S8 diagnostic build: tb_s8dbg (N=2 qfd_dv_s8_flat) with the s8die source list + the s8 kit flags, -O0 C++.
E=/srv/opentallas-scratch2/claude/tok-qw/s8exp; T=$E/tree; D=$E/dbg
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd $T; t0=$(date +%s)
verilator --cc --exe --build -O1 -j ${J:-16} -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --x-assign 0 --x-initial 0 \
  +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM +define+OT_QFD_UP4_CK_ENTRIES \
  --top-module tb_s8dbg --prefix Vtb -GN=${NS:-2} -GDBG=1 -CFLAGS -O0 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
  -Mdir $D/obj rtl/test/qwen_dv/main2.cpp $(cat $D/src/files.txt) $D/src/tb_s8dbg.sv > $D/build.log 2>&1
echo "rc=$? $(( $(date +%s)-t0 )) s" >> $D/build.log; tail -3 $D/build.log
