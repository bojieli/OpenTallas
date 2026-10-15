#!/usr/bin/env bash
# Run only inside ot-run. Independent TP4 mapping mutant must fail numerically.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory}; wrong_tp=${2:-0}
mkdir -p "$out"
sha256sum "$root/rtl/qwen_sys/native_memory_20261014/tb_native_cbuf_tp8.sv" "$root/rtl/qwen_sys/system_20261008/ot_qfd_crom.sv" "$root/rtl/qwen_sys/redesign_qwen/ot_qfd_crom_lbuf.sv" "$root/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" "$root/rtl/hdc/ot_hdc_delay.sv" "$root/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v" "$root/tools/qwen_native_memory/make_crom_fixture.py" > "$out/source.sha256"
python3 "$root/tools/qwen_native_memory/make_crom_fixture.py" "$out/masks"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --binary --timing -j 4 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
 --top-module tb_native_cbuf_tp8 -GWRONG_TP="$wrong_tp" --Mdir "$out/obj" \
 "$root/rtl/qwen_sys/native_memory_20261014/tb_native_cbuf_tp8.sv" \
 "$root/rtl/qwen_sys/redesign_qwen/ot_qfd_crom_lbuf.sv" \
 "$root/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" \
 "$root/rtl/qwen_sys/system_20261008/ot_qfd_crom.sv" \
 "$root/rtl/hdc/ot_hdc_delay.sv" \
 "$root/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v" > "$out/build.log" 2>&1
"$out/obj/Vtb_native_cbuf_tp8" +OT_ROM_DIR="$out/masks" > "$out/run.log" 2>&1
cat "$out/run.log"
if [[ "$wrong_tp" = 0 ]]; then grep -q '^PASS' "$out/run.log"; else grep -q '^FAIL' "$out/run.log"; fi
