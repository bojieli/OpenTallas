#!/bin/bash
# MU-LEAF-KIT 2026-10-19 (FLEET only, Verilator 5.050 = the closure daemon's): lockstep of the hardened leaf
# qfd_sys_face_mu_dhuser OPSEG 1 PINREG 1 against PINREG 0 on the F16 leaf ROM image (tb_dhuser_pinreg.sv).
#   usage: run_dhuser_pinreg.sh WORK MUT [+DRIFT]
#   MUT 0 (with and without +DRIFT) PASS; MUT 4 (entry one edge late), 5 (re-anchor every L0), 6 (drift check dropped,
#   with +DRIFT), 7 (PINREG without the anchor compensation) FAIL.
# Files read: rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv, rtl/test/mu_qwen_seq/tb_dhuser_pinreg.sv,
#   physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v, results/rtl/mu_qwen_1018/b1/rom/qfd_tt_ctlm_opseg.viamap.hex
set -u
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); W=${1:?WORK}; M=${2:?MUT}; shift 2
mkdir -p "$W"; W=$(cd "$W" && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
export PATH=$(dirname "$VL"):$PATH VERILATOR=$VL
verilator --version
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_dhuser_pinreg -GMUT=$M -Mdir "$W/obj" -o sim \
    "$R/physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" \
    "$R/rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv" "$D/tb_dhuser_pinreg.sv" > "$W/build.log" 2>&1 \
    || { tail -30 "$W/build.log"; echo "TB_DHUSER_PINREG BUILD_FAIL MUT=$M"; exit 2; }
"$W/obj/sim" +OT_ROM_DIR="$R/results/rtl/mu_qwen_1018/b1/rom" "$@" | tee "$W/sim.log"
grep -q '^TB_DHUSER_PINREG PASS' "$W/sim.log"
