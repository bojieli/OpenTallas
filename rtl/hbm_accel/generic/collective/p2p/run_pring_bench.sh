#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1");shift;mkdir -p "$OUT";cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
"$V" --binary --timing -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN --top-module tb_hgi_coll_pring --Mdir "$OUT/obj" "$@" \
 "$P/tb_hgi_coll_pring.sv" "$P/ot_hgi_coll_pring.sv" "$P/f32add.c" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log";exit 2; }
"$OUT/obj/Vtb_hgi_coll_pring" > "$OUT/run.log" 2>&1 || true
cat "$OUT/run.log"
grep -q '^PRING_NATIVE PASS' "$OUT/run.log"
