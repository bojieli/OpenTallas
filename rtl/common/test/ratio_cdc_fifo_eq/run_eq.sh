#!/bin/bash
# run_eq.sh <src root> <out dir>: lockstep equivalence of rtl/common/ot_ratio_cdc_fifo.sv at LOCAL_CTRL 0 against its
# pre-LOCAL_CTRL source (6fe9f807d, module renamed gold): random traffic + random resets both sides, related clocks
# 4:3 / 3:4, LAG 0 / 1, DEPTH 4 / 8.  Every closed tile built from the old source keeps its function (no re-route).
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
SRC=$1; OUT=$2; mkdir -p $OUT; D=$SRC/rtl/common/test/ratio_cdc_fifo_eq
sed 's/module ot_ratio_cdc_fifo/module gate/' $SRC/rtl/common/ot_ratio_cdc_fifo.sv > $OUT/gate.sv
v=PASS
for c in "0 4 4 3" "1 4 4 3" "0 8 3 4" "1 8 3 4" "0 4 3 4"; do set -- $c
  d=$OUT/b_$1_$2_$3_$4
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_eq -GLAG=$1 -GDEPTH=$2 -GTW=$3 -GTR=$4 --Mdir $d -o tb \
    $D/gold_ot_ratio_cdc_fifo_6fe9f807d.sv $OUT/gate.sv $D/tb_eq.sv > $d.log 2>&1 || { echo BUILD_FAIL $d; v=FAIL; continue; }
  r=$($d/tb | grep EQ); echo "$r"; case "$r" in *EQUAL) ;; *) v=FAIL;; esac
done
echo "RATIO_CDC_FIFO_EQ $v"; [ $v = PASS ]
