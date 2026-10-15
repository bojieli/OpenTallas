#!/bin/bash
set -eu
out=$1
mkdir -p "$out/masks"
python3 - "$out/masks" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1])
for tile,bank,col,one in [(2,1,0,1),(2,1,1,0),(7,4,0,0),(7,4,1,1)]:
 (p/f'qtile_t{tile}_b{bank}_c{col}.viamap.hex').write_text((('f'*532 if one else '0'*532)+'\n')*512)
PY
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_rpair_mask_identity --Mdir "$out/obj" rtl/test/qwen_tile_masks/tb_rpair_mask_identity.sv rtl/physical/ot_qwen_tile_rpair.sv rtl/hdc/ot_qwen_rom_tile_w12.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v >"$out/build.log" 2>&1
"$out/obj/Vtb_rpair_mask_identity" +OT_ROM_DIR="$out/masks" >"$out/positive.log" 2>&1
rm "$out/masks/qtile_t7_b4_c1.viamap.hex"
if "$out/obj/Vtb_rpair_mask_identity" +OT_ROM_DIR="$out/masks" >"$out/missing.log" 2>&1;then echo 'missing mask failed to fail';exit 1;fi
cat "$out/positive.log" "$out/missing.log"
