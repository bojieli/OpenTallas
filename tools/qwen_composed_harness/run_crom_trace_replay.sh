#!/usr/bin/env bash
# Q-FUNC: replay one rank's recorded constant reads through native CBUF + CROM (released masks). Run inside ot-run.
# usage: run_crom_trace_replay.sh SRC_ROOT MASK_DIR TRACE OUT
set -euo pipefail
src=${1:?}; masks=${2:?}; trace=${3:?}; out=${4:?}
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
h=$src/tools/qwen_composed_harness
mkdir -p "$out"
python3 -I "$h/crom_trace_vectors.py" "$trace" --out "$out/vec" > "$out/vectors.log" 2>&1
n=$(python3 -c "import json;print(json.load(open('$out/vec/manifest.json'))['reads'])")
rtl=("$h/tb_crom_trace_replay.sv" "$src/rtl/qwen_sys/redesign_qwen/ot_qfd_crom_lbuf.sv"
     "$src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
     "$src/rtl/qwen_sys/system_20261008/ot_qfd_crom.sv" "$src/rtl/hdc/ot_hdc_delay.sv"
     "$src/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v")
sha256sum "${rtl[@]}" "$h/crom_trace_vectors.py" "$0" > "$out/source.sha256"
nmax=$((n + 16))
for mut in 0 1; do
 "$v" --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_crom_trace_replay \
   -GMUT=$mut -GNMAX=$nmax --Mdir "$out/obj$mut" "${rtl[@]}" > "$out/build$mut.log" 2>&1
done
"$out/obj0/Vtb_crom_trace_replay" +OT_ROM_DIR="$masks" +V="$out/vec" +N="$n" > "$out/positive.log" 2>&1 || true
"$out/obj1/Vtb_crom_trace_replay" +OT_ROM_DIR="$masks" +V="$out/vec" +N="$n" > "$out/mutant_rtl.log" 2>&1 || true
cat "$out/vectors.log"; grep -h -E "^(PASS|FAIL|MISMATCH|RESIDENCY|FAULT)" "$out/positive.log" | head -8
grep -h -E "^(PASS|FAIL)" "$out/mutant_rtl.log"
grep -q '^PASS' "$out/positive.log" && grep -q '^FAIL' "$out/mutant_rtl.log"
