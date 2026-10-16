#!/usr/bin/env bash
# fe-push-hgi-1010/kv8: exact bench of ot_hgi_att_sector_codec (all 65,536 BF16 patterns incl. +-0 / subnormals /
# inf / NaN as faults, all 256 raw FP8 bytes, the FP32 E4M3 grid + off-grid / nonfinite faults + random).
# usage: run_att_sector.sh <outdir> [MUT_SECTOR_ADDR]   -> ATT_SECTOR PASS / FAIL
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_att_sector}"); MUT=${2:-}
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
python3 tools/hgi_adapters/att_sector_bench.py --out "$OUT/vec" > "$OUT/gen.log"
D=""; [ -n "$MUT" ] && D="-D$MUT"
"$VL" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED $D --top-module tb_hgi_att_sector -I"$OUT/vec" \
  -Mdir "$OUT/obj" rtl/hbm_accel/generic/peers/ot_hgi_att_sector_codec.sv rtl/hbm_accel/generic/adapters/tb/tb_hgi_att_sector.sv \
  > "$OUT/build.log" 2>&1 || { tail -20 "$OUT/build.log"; echo "ATT_SECTOR FAIL (build)"; exit 2; }
(cd "$OUT/vec" && "$OUT/obj/Vtb_hgi_att_sector") > "$OUT/run.log" 2>&1 || true
cat "$OUT/run.log" | tail -3
if grep -q "ATT_SECTOR PASS" "$OUT/run.log"; then echo "ATT_SECTOR PASS"; else echo "ATT_SECTOR FAIL"; exit 1; fi
