#!/usr/bin/env bash
# Q-FUNC native CROM with released stage images. Run inside ot-run on the host holding the banks.
# usage: run_crom_released.sh SRC_ROOT IMAGES_DIR HEAD_CROM OUT
set -euo pipefail
src=${1:?source root}; images=${2:?banks/images}; head=${3:?head crom.hex}; out=${4:?fresh out dir}
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
h=$src/tools/qwen_composed_harness
mkdir -p "$out"
python3 -I "$h/crom_native_masks.py" --images "$images" --head-crom "$head" --out "$out/masks" > "$out/export.log" 2>&1
n=$(python3 -c "import json;print(json.load(open('$out/masks/manifest.json'))['tests'])")
rtl=("$h/tb_crom_released_tp8.sv" "$src/rtl/qwen_sys/system_20261008/ot_qfd_crom.sv" "$src/rtl/hdc/ot_hdc_delay.sv"
     "$src/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v")
sha256sum "${rtl[@]}" "$h/crom_native_masks.py" "$0" > "$out/source.sha256"
build() { "$v" --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_crom_released_tp8 \
    -GMUT="$1" --Mdir "$2" "${rtl[@]}" > "$2.build.log" 2>&1; }
build 0 "$out/obj"; build 1 "$out/obj_mut"
# positive
"$out/obj/Vtb_crom_released_tp8" +OT_ROM_DIR="$out/masks" +TESTS="$out/masks" +N="$n" > "$out/positive.log" 2>&1 || true
# mutant A: RTL output mutant (lane 0 bit 0)
"$out/obj_mut/Vtb_crom_released_tp8" +OT_ROM_DIR="$out/masks" +TESTS="$out/masks" +N="$n" > "$out/mutant_rtl.log" 2>&1 || true
# mutant B: one mask bit flipped in a narrow macro (row of layer 0 QK tile) -> data must mismatch
mkdir -p "$out/masks_mut"; cp "$out/masks"/crom_*.viamap.hex "$out/masks_mut/"
python3 -I - "$out/masks_mut/crom_n_c0_d0.viamap.hex" <<'PY'
import sys
p=sys.argv[1]; L=open(p).read().split('\n')
# narrow row 0 (layer0 QK row 0), lane 0 bit 3: physical row 0, column bit 3*8+0
x=int(L[0],16)^(1<<24); L[0]=f'{x:0532x}'; open(p,'w').write('\n'.join(L))
PY
"$out/obj/Vtb_crom_released_tp8" +OT_ROM_DIR="$out/masks_mut" +TESTS="$out/masks" +N="$n" > "$out/mutant_mask.log" 2>&1 || true
rm -rf "$out/masks_mut"
grep -h -E "^(PASS|FAIL)" "$out/positive.log" "$out/mutant_rtl.log" "$out/mutant_mask.log"
grep -q '^PASS' "$out/positive.log" && grep -q '^FAIL' "$out/mutant_rtl.log" && grep -q '^FAIL' "$out/mutant_mask.log"
