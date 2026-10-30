#!/usr/bin/env bash
# Reproduce the unused component coupon in an owned scratch directory.
set -euo pipefail
STATIC_LOAD_ROOT=$1
STATIC_LOAD_RUN=$2
STATIC_LOAD_SOURCE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$STATIC_LOAD_RUN"
cp "$STATIC_LOAD_SOURCE/ot_hbm_static_load_decode.sv" "$STATIC_LOAD_SOURCE/tb_static_load_decode.sv" "$STATIC_LOAD_SOURCE/fp8_truth.mem" "$STATIC_LOAD_SOURCE/i8_truth.mem" "$STATIC_LOAD_SOURCE/ue8_truth.mem" "$STATIC_LOAD_RUN/"
cp "$STATIC_LOAD_ROOT/rtl/hbm_accel/generic/peers/ot_hgi_dma_mover_serial.sv" "$STATIC_LOAD_RUN/native_mover_serial.sv"
python3 - "$STATIC_LOAD_ROOT" "$STATIC_LOAD_RUN" <<'PY'
from pathlib import Path
import sys
source=Path(sys.argv[1], 'rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_vmdel_lane_load_static.sv').read_text()
start=source.index('module ot_hbm_dma_convert_part ')
end=source.index('endmodule',start)+len('endmodule')
Path(sys.argv[2], 'native_convert_part.sv').write_text(source[start:end]+'\n')
PY
cd "$STATIC_LOAD_RUN"
verilator --lint-only -Wall -Wno-DECLFILENAME --top-module ot_hbm_static_load_decode ot_hbm_static_load_decode.sv > lint.log 2>&1
iverilog -g2012 -s tb_static_load_decode -o baseline.vvp ot_hbm_static_load_decode.sv tb_static_load_decode.sv native_mover_serial.sv native_convert_part.sv > compile.log 2>&1
vvp baseline.vvp > baseline.log 2>&1
iverilog -g2012 -s tb_static_load_decode -Ptb_static_load_decode.MUT=1 -o mutant.vvp ot_hbm_static_load_decode.sv tb_static_load_decode.sv native_mover_serial.sv native_convert_part.sv > mutant_compile.log 2>&1
if vvp mutant.vvp > mutant.log 2>&1; then
  echo 'FAIL: wrong FP8 subnormal mutant escaped' >&2
  exit 1
fi
rg -q 'MUTANT_OR_FAILURE caught 8 mismatches' mutant.log
cat baseline.log
printf 'PASS: native lockstep and seeded arithmetic mutant caught\n'
