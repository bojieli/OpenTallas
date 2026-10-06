#!/usr/bin/env bash
# Build the dual-clock Verilator bench of ot_meso_fifo.
# Usage: build_tb.sh OUTDIR [DEPTH] [OFFSET] [GUARD_LO] [GUARD_HI] [CREDITS] [EXTRA_DEFINE]   (env RDREG=1: readout flops; NOBP=1: no receive buffer)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=$1; DEPTH=${2:-4}; OFFSET=${3:-2}; GLO=${4:-0}; GHI=${5:-4}; CRED=${6:-8}; EXTRA=${7:-}
mkdir -p "$OUT"
verilator --cc --exe -O3 --x-assign unique --x-initial unique -Wno-fatal -Wno-DECLFILENAME \
  -DOT_MESO_DEBUG ${EXTRA:+-D$EXTRA} -CFLAGS "-O2 -DDEPTH_=$DEPTH" \
  -GW=512 -GENABLE=1 -GDEPTH=$DEPTH -GSETTLE=$(( DEPTH > 8 ? DEPTH : 8 )) -GOFFSET=$OFFSET -GGUARD_LO=$GLO -GGUARD_HI=$GHI -GCREDITS=$CRED ${RDREG:+-GRDREG=$RDREG} ${NOBP:+-GNOBP=$NOBP} \
  --top-module ot_meso_fifo "${RTL:-$ROOT/rtl/common/ot_meso_fifo.sv}" "$ROOT/rtl/test/meso/tb_meso_fifo.cpp" \
  -Mdir "$OUT" -o tb > "$OUT/verilate.log" 2>&1
make -s -C "$OUT" -f Vot_meso_fifo.mk -j8 > "$OUT/make.log" 2>&1
echo "$OUT/tb"
