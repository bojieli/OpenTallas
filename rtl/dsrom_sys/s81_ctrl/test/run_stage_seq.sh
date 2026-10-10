#!/bin/bash
# run_stage_seq.sh <src root> <out dir> [QD] [MUT] [L]: build tb_s81_stage_seq (Verilator 5) and run every stage program
# of <src>/results/rtl/s81_ctrl_20261008/programs/hex; one TB_S81_STAGE_SEQ line per program in <out>/run_q<QD>_m<MUT>.log
set -u
SRC=$1; OUT=$2; QD=${3:-4}; MUT=${4:-0}; L=${5:-4}
B=$OUT/b_q${QD}_m${MUT}_l${L}; mkdir -p $B
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_stage_seq \
  -GQD=$QD -GMUT=$MUT -GL_CMD=$L -GL_DN=$L --Mdir $B -o tb \
  $SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv $SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_stage_seq.sv > $B/build.log 2>&1 || { echo BUILD_FAIL; tail -20 $B/build.log; exit 1; }
LOG=$OUT/run_q${QD}_m${MUT}_l${L}.log; : > $LOG
for h in $SRC/results/rtl/s81_ctrl_20261008/programs/hex/*.hex; do
  nops=$(grep -c . $h)
  timeout 600 $B/tb +prog=$h +nops=$nops 2>&1 | grep TB_S81 >> $LOG || echo "TB_S81_STAGE_SEQ prog=$h TIMEOUT_OR_CRASH FAIL" >> $LOG
done
echo "PASS $(grep -c ' PASS$' $LOG) FAIL $(grep -c FAIL $LOG)"
