#!/usr/bin/env bash
# QC-P5-TIE slice lockstep (tb_s8_ce, VAR 1 = e5 incl. sc_dn end, VAR 2 = w5).  usage: build.sh VAR MUT
set -u; VAR=$1; MUT=$2; OUT=out_v${VAR}m${MUT}; mkdir -p $OUT
export OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
VF="--binary --timing -O2 -j 48 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --x-assign 0 --x-initial 0 +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM"
$V --version > $OUT/verilator_version.txt
$V $VF -GVAR=$VAR -GMUT=$MUT --top-module tb_s8_ce $(cat files.txt) -Mdir $OUT/obj > $OUT/build.log 2>&1 || { echo "BUILD FAIL $VAR $MUT"; grep -m20 '%Error' $OUT/build.log; exit 1; }
$OUT/obj/Vtb_s8_ce > $OUT/run.log 2>&1
grep -m8 "CE_MISMATCH\|S8_CE_LOCKSTEP" $OUT/run.log
