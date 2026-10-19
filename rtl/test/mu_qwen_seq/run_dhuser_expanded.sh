#!/bin/bash
# FLEET only. Positive MUT0/BAD_BANK0 must PASS; MUT7 or BAD_BANK1 must FAIL.
# Usage: WORK ROM_DIR EXPECTED [MUT] [BAD_BANK]. Reads allthree compiledROMimages.
set -eu
D=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$D/../../.." && pwd)
W=${1:?WORK}; ROM=${2:?ROM_DIR}; EXPECT=${3:?EXPECTED}; MUT=${4:-0}; BAD=${5:-0}
mkdir -p "$W/obj"; W=$(cd "$W" && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_dhuser_expanded \
    -GMUT="$MUT" -GBAD_BANK="$BAD" -Mdir "$W/obj" -o sim \
    "$R/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" \
    "$R/rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv" "$D/tb_dhuser_expanded.sv" > "$W/build.log" 2>&1
"$W/obj/sim" +OT_ROM_DIR="$ROM" +EXPECTED="$EXPECT" | tee "$W/sim.log"
grep -q '^TB_DHUSER_EXPANDED PASS' "$W/sim.log"
