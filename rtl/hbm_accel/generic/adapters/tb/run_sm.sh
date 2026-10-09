#!/usr/bin/env bash
# hgi-adapters: ot_hgi_sm_record bench.  usage: run_sm.sh <outdir> [MUT_ROWS|MUT_EARLY]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_sm_run}"); MUT=${2:-}
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
python3 tools/hgi_adapters/sm_bench.py --out "$OUT/vec" > "$OUT/gen.log"
D=""; [ -n "$MUT" ] && D="-D$MUT"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT --top-module tb_hgi_sm_record \
  -I"$OUT/vec" $D -Mdir "$OUT/obj${MUT:+_$MUT}" rtl/hbm_accel/generic/adapters/ot_hgi_sm_record.sv \
  rtl/hbm_accel/generic/adapters/tb/tb_hgi_sm_record.sv -j 8 > "$OUT/build${MUT:+_$MUT}.log" 2>&1 || { tail -30 "$OUT/build${MUT:+_$MUT}.log"; exit 2; }
"$OUT/obj${MUT:+_$MUT}/Vtb_hgi_sm_record" +DIR="$OUT/vec" | tee "$OUT/run${MUT:+_$MUT}.log" | tail -12
