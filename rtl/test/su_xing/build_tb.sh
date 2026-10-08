#!/usr/bin/env bash
# Build the three-clock bench of the DS-ROM SU crossing (meso + ratio FIFO each way).  Usage: build_tb.sh OUTDIR
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=$1
mkdir -p "$OUT"
${VERILATOR:-verilator} --cc --exe -O3 --x-assign unique --x-initial unique -Wno-fatal -Wno-DECLFILENAME -CFLAGS -O2 \
  --top-module tb_su_xing_top "$ROOT/rtl/common/ot_meso_fifo.sv" "$ROOT/rtl/common/ot_ratio_cdc_fifo.sv" \
  "$ROOT/rtl/test/su_xing/tb_su_xing_top.sv" "$ROOT/rtl/test/su_xing/tb_su_xing.cpp" \
  ${OT_XING_FLAGS:-} -Mdir "$OUT" -o tb > "$OUT/verilate.log" 2>&1
make -s -C "$OUT" -f Vtb_su_xing_top.mk -j8 > "$OUT/make.log" 2>&1
echo "$OUT/tb"
