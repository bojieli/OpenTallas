#!/bin/bash
set -euo pipefail
P=/srv/opentallas-scratch2/claude/fable-fix-s81-serdes/xface_retime1117
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$P/bench_profileH"
verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -Wno-LITENDIAN -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb_xface -DOT_S81_RCK_XPIPE1 -DOT_KP4_DEC_HARD -DOT_S81_SERDES_TXPIPE -DOT_S81_SERDES_RXPIPE -DOT_S81_SERDES_RXNEG -DOT_S81_SERDES_RST_TREE -DOT_S81_KP4_AM_FACE3 -DOT_S81_RCK_RELAY4 -DOT_S81_SERDES_RM_RPC8 -DOT_S81_SERDES_BOOT_RELEASE3 +incdir+$PWD/src -f sources.f --Mdir obj -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0" > build.log 2>&1
./obj/Vtb_xface > run.log 2>&1
grep -q XFACE_FULL_DECODER_PASS run.log
