#!/usr/bin/env bash
# Run only inside an admitted ot-run staged repository job.
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:?output directory required}
mkdir -p "$OUT"
for kind in best64 host276; do
  verilator --binary --timing -j "${BUILD_THREADS:-2}" -Wno-fatal \
    --top-module "tb_s81hd_$kind" --Mdir "$OUT/obj_$kind" \
    "$ROOT/rtl/dsrom_sys/s81_head/ot_s81hd_beat_link.sv" \
    "$ROOT/rtl/dsrom_sys/s81_head/ot_s81hd_$kind.sv" \
    "$ROOT/rtl/dsrom_sys/s81_head/test/tb_s81hd_$kind.sv" \
    > "$OUT/${kind}_build.log" 2>&1
  "$OUT/obj_$kind/Vtb_s81hd_$kind" > "$OUT/$kind.log" 2>&1
  cat "$OUT/$kind.log"
done
