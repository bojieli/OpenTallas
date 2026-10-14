#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(realpath -m "$1"); MODE=${2:-exact}; mkdir -p "$OUT"; cd "$ROOT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
RTL=rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv
if [ "$MODE" = mutant ]; then
  python3 - "$RTL" "$OUT/mutant.sv" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();old='o_data<=relay_d[31:0];';assert s.count(old)==1
Path(sys.argv[2]).write_text(s.replace(old,"o_data<=relay_d[31:0] ^ 32'd1;"))
PY
  RTL=$OUT/mutant.sv
fi
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_smpub_parent -Mdir "$OUT/obj" -j "${J:-8}" \
 rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$RTL" \
 rtl/hbm_accel/generic/adapters/tb/smpub_parent/smpub_parent_reference.sv \
 rtl/hbm_accel/generic/adapters/tb/smpub_parent/tb_smpub_parent.sv > "$OUT/build.log" 2>&1
set +e
"$OUT/obj/Vtb_smpub_parent" > "$OUT/run.log" 2>&1
bench_rc=$?
set -e
cat "$OUT/run.log"
exit "$bench_rc"
