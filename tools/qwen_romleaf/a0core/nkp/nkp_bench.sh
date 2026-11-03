#!/bin/bash
# DIE-QC-66/CORES-NK: build + run the NK NKP bench.  usage: nkp_bench.sh RTLDIR MAINSRC OUT [TB]
set -uo pipefail
RTL=$1; M=$2; OUT=$(mkdir -p "$3" && realpath "$3"); TB=${4:-$(dirname $(realpath $0))/tb_a0_nkp.sv}; V=$HOME/.local/opentallas-tools/bin/verilator
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
$V --binary --timing -j 16 -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DOT_ROM_CONST0_KV -DOT_A0_LOCAL_OUT_RESET ${VDEFS:-} \
  --top-module tb_a0_nkp -Mdir $OUT/obj $TB "${SRC[@]}" > $OUT/build.log 2>&1 || { echo BUILD_FAIL; tail -30 $OUT/build.log; exit 1; }
echo BUILD_OK
for m in ${MUTS:-0 1 2 3}; do X=; [ $m = 6 ] && X=+ICG_MUT=16; $OUT/obj/Vtb_a0_nkp +OT_ROM_DIR=$OUT/rom +MUT=$m $X > $OUT/run_mut$m.log 2>&1 & done; wait
grep -h '^NKP_\|%Fatal\|%Error' $OUT/run_mut*.log
