#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "${1:?output directory required}")
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"
cd "$ROOT"
for m in 0 1 2 3; do
  d="$OUT/m$m"; mkdir -p "$d"
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -Wno-LATCH -DWMUT=$m --top-module tb_hgi_sv_native_write_owned -Mdir "$d/obj" -j "${J:-4}" rtl/hbm_accel/generic/peers/ot_hgi_sv_native_write_owned.sv rtl/hbm_accel/generic/peers/tb_hgi_sv_native_write_owned.sv > "$d/build.log" 2>&1
  "$d/obj/Vtb_hgi_sv_native_write_owned" > "$d/run.log" 2>&1
  if [ "$m" = 0 ]; then grep -q 'SV_NATIVE_WRITE PASS' "$d/run.log"; else grep -q 'SV_NATIVE_WRITE FAIL' "$d/run.log"; fi
  tail -5 "$d/run.log"
done
