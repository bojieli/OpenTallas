#!/bin/bash
set -eu
out=$(mkdir -p "$1" && realpath "$1");mut=${2:-0}
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_res_tiles -GMUT="$mut" -Mdir "$out/obj" rtl/test/res_tiles/tb_res_tiles.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_tiles.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$out/build.log" 2>&1
set +e
"$out/obj/Vtb_res_tiles" > "$out/run.log" 2>&1
rc=$?
cat "$out/run.log"
if [ "$mut" != 0 ]; then
 if grep -q "MISMATCH" "$out/run.log"; then echo "FAIL res_tiles mutant detected"; exit 1; fi
 echo "NEGATIVE_CONTROL_MISSED_OR_CRASHED"; exit 2
fi
exit "$rc"
