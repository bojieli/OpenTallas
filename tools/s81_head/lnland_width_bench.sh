#!/usr/bin/env bash
# Invoke inside an ot-run admitted/staged source repository.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:?new output directory required}
mkdir -p "$OUT"
cp "$ROOT/physical/die_plan/s81/bind/source_modules/portfix178/ot_s81_mu72_lnland.sv" "$OUT/new.sv"
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=(p/'new.sv').read_text()
s=s.replace('[559:0] nk','[558:0] nk').replace('.W(560)','.W(559)')
s=s.replace('[557:0] nk','[556:0] nk').replace('.W(558)','.W(557)')
s=s.replace('module ot_s81_mu72_lnland_nst ','module ot_s81_mu72_lnland_nst_old ').replace('module ot_s81_mu72_lnland ','module ot_s81_mu72_lnland_old ')
(p/'old.sv').write_text(s)
PY
cp "$ROOT/rtl/dsrom_sys/s81_head/test/tb_lnland_width.sv" "$ROOT/rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv" "$OUT/"
cp "$ROOT"/rtl/common/landed_parent/*.sv "$OUT/"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing --output-split 10000 --output-split-cfuncs 200 -j "${BUILD_THREADS:-2}" -Wno-fatal --top-module tb_lnland_width --Mdir "$OUT/obj" "$OUT"/*.sv > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_lnland_width" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
