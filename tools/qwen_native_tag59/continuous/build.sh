#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
out=${1:?output};mkdir -p "$out";out=$(cd "$out"&&pwd)
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
[[ -x "$v" ]]||v=$(command -v verilator)
sources=(rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/rom/ot_rom_oneshot_die_m.sv rtl/rom/ot_coll_fold_slice.sv rtl/rom/ot_coll_rst_leaf.sv rtl/rom/ot_coll_col_tile.sv
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/lib/ot_hdly.sv
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
 rtl/rom/ot_rom_oneshot_allreduce.sv rtl/rom/ot_coll_tp8_die.sv rtl/rom/ot_coll_tp8_col_tile.sv rtl/rom/ot_rom_oneshot_die_native59.sv rtl/rom/ot_coll_tp8_die_native59.sv rtl/physical/ot_qwen_native59_collective8.sv)
sha256sum "${sources[@]}" tools/qwen_native_tag59/continuous/native59.{h,cpp} > "$out/source_pins.sha256"
if [[ -n ${2:-} ]]; then
 reuse=$(cd "$2"&&pwd)
 # Reuse only the exact compiled RTL; bridge/header changes do not change it.
 python3 - "$reuse/source_pins.sha256" <<'VERIFY'
import hashlib,sys
from pathlib import Path
for line in Path(sys.argv[1]).read_text().splitlines():
 h,p=line.split(None,1)
 if p.endswith(('.sv','.v')):
  assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h, f'compiled RTL drift: {p}'
VERIFY
 ln -s "$reuse/obj" "$out/obj"
 sha256sum "$reuse/obj/Vnative59__ALL.a" > "$out/reused_model_archive.sha256"
else
"$v" --timescale-override 1ns/1fs --cc --build -O1 -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-UNOPTFLAT \
 --top-module ot_qwen_native59_collective8 --prefix Vnative59 --Mdir "$out/obj" "${sources[@]}" -CFLAGS -fPIC > "$out/build.log" 2>&1
fi
vroot=$("$v" -V|sed -n 's/^[[:space:]]*VERILATOR_ROOT[[:space:]]*=[[:space:]]*//p'|head -1)
g++ -std=c++17 -O1 -fPIC -shared -pthread -I"$out/obj" -I"$vroot/include" -Itools/qwen_native_tag59/continuous \
 tools/qwen_native_tag59/continuous/native59.cpp "$out/obj/Vnative59__ALL.a" "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" \
 -o "$out/libnative59.so" >> "$out/build.log" 2>&1
sha256sum "$out/libnative59.so" > "$out/executable.sha256"
echo "CONTINUOUS_NATIVE59_READY $out/libnative59.so"
