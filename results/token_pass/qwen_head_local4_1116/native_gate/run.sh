#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o build.time "$V" --binary --timing --top-module tb -j 1 -Wno-fatal -Wno-lint -Wno-style --Mdir obj -f sources.f > build.log 2>&1
./obj/Vtb +OT_QC_TABLE_ROM_DIR=masks > run.log 2>&1
./obj/Vtb +OT_QC_TABLE_ROM_DIR=wrong_masks +EXPECT_FAIL > wrong_mask.log 2>&1
./obj/Vtb +OT_QC_TABLE_ROM_DIR=masks +GAP=90 > admission90.log 2>&1
./obj/Vtb +OT_QC_TABLE_ROM_DIR=masks +GAP=89 +EXPECT_ADMISSION_FAIL > admission89.log 2>&1
cat run.log wrong_mask.log admission90.log admission89.log
grep -q 'LOCAL4_GATE_PASS negative=0' run.log
grep -q 'LOCAL4_GATE_PASS negative=1' wrong_mask.log

grep -q "LOCAL4_GATE_PASS negative=0" admission90.log
grep -q "ADMISSION_REJECT_CAUGHT gap=89" admission89.log
