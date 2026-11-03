#!/bin/bash
# DIE-QC-66/CORES: build + run the NL IDLE_UCK bench.  usage: bench.sh RTLDIR(NL kit rtl, IDLE_UCK-patched) MAINSRC(repo root for behavioural models) OUT
set -uo pipefail
TB=${TB:-$(dirname "$(realpath "$0")")/tb_a0_idleuck.sv}
RTL=$1; M=$2; OUT=$(mkdir -p "$3" && realpath "$3"); V=$HOME/.local/opentallas-tools/bin/verilator
SRC=()
for f in "$RTL"/*.sv "$RTL"/*.v; do b=$(basename "$f"); [[ $b == *_bb.v || $b == ot_qwen_tile_lsl_rawcut.v ]] || SRC+=("$f"); done
SRC+=($M/rtl/physical/ot_qwen_tile_romleaf.sv $M/rtl/physical/ot_qwen_tile_lsl_fp1.sv $M/rtl/physical/ot_qwen_tile_lsl.sv $M/rtl/physical/ot_qwen_tile_node.sv
  $M/rtl/physical/ot_qwen_tile_operand.sv $M/rtl/physical/ot_qwen_tile_rqr_half.sv $M/rtl/physical/ot_qwen_tile_rpair.sv
  $M/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v $M/physical/asap7_memory_macros/ot_rom_2048x266_m8/ot_rom_2048x266_m8.v
  $M/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
printf '%s\n' "${SRC[@]}" > $OUT/files.txt
sha256sum "${SRC[@]}" $TB > $OUT/sources.sha256
python3 -I $M/tools/qwen_romleaf/a0core/equiv/gen_rom.py $OUT/rom 48 > /dev/null
rm -rf $OUT/obj
$V --binary --timing -j 16 -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DOT_ROM_CONST0_KV \
  --top-module tb_a0_idleuck -Mdir $OUT/obj $TB "${SRC[@]}" > $OUT/build.log 2>&1 || { echo BUILD_FAIL; tail -30 $OUT/build.log; exit 1; }
echo BUILD_OK
for m in 0 1 2; do $OUT/obj/Vtb_a0_idleuck +OT_ROM_DIR=$OUT/rom +MUT=$m > $OUT/run_mut$m.log 2>&1 & done; wait
grep -h '^IDLEUCK_\|%Fatal\|%Error' $OUT/run_mut*.log
