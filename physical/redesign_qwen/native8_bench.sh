#!/bin/bash
# STRAP=1 (env, qwen-1010/c): all 8 groups are the strap tile ot_qfd_crom_gs (crom_lb = 8 g); MUT 5 = one wrong strap.
set -u
mut=$1
out=$(mkdir -p "$2" && readlink -f "$2")
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$v" ] || v=verilator
python3 - "$out/img" <<'PY'
import random,sys
from pathlib import Path
p=Path(sys.argv[1]);p.mkdir(exist_ok=True);random.seed(7)
names=[f'crom_w_c{c}_d{d}' for c in range(16) for d in range(2)]
names += [f'crom_n_c{c}_d{d}' for c in range(8) for d in range(2)]
for n in names:
    with (p/(n+'.viamap.hex')).open('w') as f:
        for row in range(512): f.write('%0532x\n' % random.getrandbits(2128))
PY
"$v" --binary -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-DECLFILENAME \
 -Wno-INITIALDLY -Wno-TIMESCALEMOD -GMUT="$mut" -GSTRAP="${STRAP:-0}" --top-module tb_qfd_crom_native8 \
 -Mdir "$out/obj" rtl/qwen_sys/system_20261008/ot_qfd_crom.sv rtl/hdc/ot_hdc_delay.sv \
 rtl/qwen_sys/redesign_qwen/ot_qfd_crom_native8.sv \
 physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v \
 rtl/test/redesign_qwen/tb_qfd_crom_native8.sv > "$out/build.log" 2>&1 \
 || { echo BUILD_FAIL native8; exit 2; }
"$out/obj/Vtb_qfd_crom_native8" +OT_ROM_DIR="$out/img" > "$out/run.log" 2>&1
rc=$?
cat "$out/run.log"
if [ "$mut" = 0 ]; then
 [ "$rc" = 0 ] && grep -q '^PASS native8' "$out/run.log" && exit 0
 echo FAIL native8 positive; exit 1
fi
if [ "$rc" != 0 ] && grep -q 'MISMATCH native8' "$out/run.log"; then
 echo "FAIL native8 mutant detected MUT=$mut"; exit 1
fi
echo "FAIL native8 mutant gate invalid MUT=$mut rc=$rc"; exit 2
