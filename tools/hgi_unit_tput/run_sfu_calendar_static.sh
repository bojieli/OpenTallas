#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
calendar=${SFU_CALENDAR_SOURCE:-rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv}
printf '%s  %s\n' 2a3f380c413bef2676087338d00d18cf869562e9bb611fc93c13251f3fb3f197 "$calendar" | sha256sum -c -
python3 - "$OUT/image.hex" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,'tools/hbm_static')
from sfu_vector_calendar import compile_vector
from sfu_control_image import encode
words=encode(compile_vector(words=7168,bases=(0,0,0,0,0),sfu=4))
assert len(words)==624
Path(sys.argv[1]).write_text(''.join(f'{word:0436x}\n' for word in words))
PY
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O1 -j 4 -CFLAGS -O0 -Wno-fatal --top-module tb_hgi_sfu_calendar_static --Mdir "$OUT/obj" "-DSFU_IMAGE=\"$OUT/image.hex\"" \
 "$calendar" rtl/hbm_accel/generic/peers/ot_hgi_sfu_calendar_static.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_calendar_static.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_calendar_static" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
set +e
"$OUT/obj/Vtb_hgi_sfu_calendar_static" +MUT_PC > "$OUT/mutant.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -Eq 'SFU_PROGRAM_(IDENTITY|WORD)' "$OUT/mutant.log";then cat "$OUT/mutant.log";exit 1;fi
printf 'PASS actual programme PC-identity mutant rc=%s\n' "$rc"
