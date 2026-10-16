#!/bin/bash
# redesign-qwen 2026-10-09: 8 constant-ROM group tiles == the 64-lane ot_qfd_crom (random mask images, contract reads).
#   crom_g_bench.sh pos OUT -> CROM_G_PASS ; crom_g_bench.sh neg OUT (GMUT 1: wrong lane bases) -> CROM_G_NEG_DETECTED (rc 1)
set -u
m=$1; o=$(mkdir -p "$2" && readlink -f "$2")
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
python3 - "$o/img" <<'PY'
import os, random, sys
d = sys.argv[1]; os.makedirs(d, exist_ok=True); random.seed(7)
for n in [f"crom_w_c{c}_d{k}" for c in range(16) for k in range(2)] + [f"crom_n_c{c}_d{k}" for c in range(8) for k in range(2)]:
    with open(f"{d}/{n}.viamap.hex", "w") as f:
        for r in range(512): f.write("%0532x\n" % random.getrandbits(2128))
PY
g=$([ $m = neg ] && echo 1 || echo 0)
$V --binary -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-DECLFILENAME -Wno-INITIALDLY -Wno-TIMESCALEMOD -GGMUT=$g --top-module tb_qfd_crom_g \
   -Mdir "$o/obj" rtl/qwen_sys/system_20261008/ot_qfd_crom.sv rtl/hdc/ot_hdc_delay.sv \
   physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v rtl/test/redesign_qwen/tb_qfd_crom_g.sv > "$o/build.log" 2>&1 || { echo BUILD_FAIL; exit 2; }
"$o/obj/Vtb_qfd_crom_g" +OT_ROM_DIR="$o/img" > "$o/run.log" 2>&1
if [ $m = pos ]; then grep -q '^PASS crom_g' "$o/run.log" && { echo CROM_G_PASS; exit 0; }; echo CROM_G_FAIL; exit 1; fi
grep -q '^PASS crom_g' "$o/run.log" && { echo CROM_G_NEG_MISSED; exit 0; }; echo CROM_G_NEG_DETECTED; exit 1
