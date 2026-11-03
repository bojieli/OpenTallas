#!/bin/bash
set -euo pipefail
ulimit -c 0
R="${BF_RUN_DIR:-/srv/opentallas-scratch2/claude/codex-ds-bf-native-pair-0605}"
cd "$R"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=(+define+DSFD_PQ_STATIC_X2 +define+DSFD_PQ_HAS_BF_X2 +define+S81CTRL_SRAM_FIFO +define+S81CTRL_SRAM_P192 +define+S81CTRL_NATIVE32 +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF +define+OT_S81ENG_TAP_N32R2 +define+OT_S81SL_KV_TRANSPORT +define+OT_SVC_ALLQ +define+SU_SMU_T +define+OT_ATTN_HCORE +define+OT_S81ENG_RR_N32 +define+OT_S81C_HCORE_CTLA +define+OT_S81C_HCORE_RST_TIMED +define+S81_HOSTB_LAND_OBS +define+OT_S81_SH_SRAM +define+OT_S81_SH_RSZ +define+OT_S81_SH_P192 +define+OT_S81_SH_APIPE9 +define+OT_S81_SH_APIPE10)
/usr/bin/time -v "$V" --binary --timing -O1 -j 2 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-MULTITOP --output-split 20000 --output-split-cfuncs 2000 "${D[@]}" --top-module tb_bf_source_pair -Mdir "$R/obj" -f sources.f > build.log 2> build.err
./obj/Vtb_bf_source_pair +OT_ROM_DIR="$R/images" > actual.log 2>&1
