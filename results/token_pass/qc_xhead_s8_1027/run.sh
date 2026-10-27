#!/bin/bash
set -eu
E=/srv/opentallas-scratch2/claude/codex-qc-xhead-1027
T=$E/tree
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
export DV2_S8DIE=1
export DV_LOWER_VFLAGS='-GMU_NU=4 -GFACE=3 +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM +define+OT_QFD_UP4_CK_ENTRIES -Wno-WIDTHCONCAT +define+OT_S8_CROM_ALIGN'
export OT_XH_BUILD_FLAGS="-O1 -j 48 --output-split 20000 --output-split-cfuncs 10000 --output-groups 192 -CFLAGS -O0 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0'"
export OT_XH_GO_MIN=-10
mkdir -p $E/build $E/cal
cd $T
python3 rtl/test/qwen_dv/xhead_bench.py --calibrate --work $E/cal --build-dir $E/build --vec-ages $E/cal/vec_ages.json > $E/calibrate.log 2>&1
