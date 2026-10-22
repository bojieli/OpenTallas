#!/usr/bin/env bash
set -eu
B=tools/qwen_kv_die/pv_join_s32/bench.sh
bash $B "$PWD/pvj_m0" 0
if bash $B "$PWD/pvj_m1" 1; then echo "MUTANT 1 NOT CAUGHT"; exit 1; fi
if bash $B "$PWD/pvj_m2" 2; then echo "MUTANT 2 NOT CAUGHT"; exit 1; fi
if bash $B "$PWD/pvj_m3" 0 -DPVJ32_MUT3; then echo "MUTANT 3 NOT CAUGHT"; exit 1; fi
echo "PVJ32 SUITE PASS"
