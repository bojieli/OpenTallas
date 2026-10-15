#!/usr/bin/env bash
# Q-FUNC join960: replay one rank's recorded core constant reads through the join's qfd_native_crom8_tp8 via the SU ca/cq ABI.
# usage (inside ot-run): run_crom8_abi_replay.sh SRC_ROOT MASK_DIR VEC_DIR(from crom_trace_vectors.py) OUT
set -euo pipefail
src=${1:?}; masks=${2:?}; vec=${3:?}; out=${4:?}
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$out"
n=$(python3 -c "import json;print(json.load(open('$vec/manifest.json'))['reads'])")
rtl=("$src/rtl/test/qwen_split/tb_crom8_abi_replay.sv" "$src/rtl/qwen_split/qfd_native_crom8_tp8.sv"
     "$src/rtl/qwen_sys/redesign_qwen/ot_qfd_crom_lbuf.sv"
     "$src/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
     "$src/rtl/qwen_sys/system_20261008/ot_qfd_crom.sv" "$src/rtl/hdc/ot_hdc_delay.sv"
     "$src/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v")
sha256sum "${rtl[@]}" "$0" > "$out/source.sha256"
for mut in 0 1; do
 "$v" --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_crom8_abi_replay \
   -GMUT=$mut -GNMAX=$((n + 16)) --Mdir "$out/obj$mut" "${rtl[@]}" > "$out/build$mut.log" 2>&1
done
"$out/obj0/Vtb_crom8_abi_replay" +OT_ROM_DIR="$masks" +V="$vec" +N="$n" > "$out/positive.log" 2>&1 || true
"$out/obj1/Vtb_crom8_abi_replay" +OT_ROM_DIR="$masks" +V="$vec" +N="$n" > "$out/mutant_rtl.log" 2>&1 || true
grep -h -E "^(PASS|FAIL|MISMATCH|RESIDENCY|FAULT)" "$out/positive.log" | head -8
grep -h -E "^(PASS|FAIL)" "$out/mutant_rtl.log"
grep -q '^PASS' "$out/positive.log" && grep -q '^FAIL' "$out/mutant_rtl.log"
