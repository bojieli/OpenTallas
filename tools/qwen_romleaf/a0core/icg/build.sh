#!/bin/bash
# DIE-QC-16 A0 ICG bench build.  usage: [ICG=1|2] build.sh TILE(nk|nl) OUTDIR [JOBS]   (run from the repo root)
set -euo pipefail
TILE=$1; OUT=$(mkdir -p "$2" && realpath "$2"); JOBS=${3:-16}
D=tools/qwen_romleaf/a0core/icg
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
eval "$(grep '^SRCS=' physical/ref_tile/qfd_tile_${TILE}_a0cv6/kit.env)"
SRC=()
for f in $SRCS; do [[ $f == *_bb.v ]] || SRC+=("$f"); done
SRC+=(rtl/physical/ot_qwen_tile_romleaf.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv rtl/physical/ot_qwen_tile_node.sv
  rtl/physical/a0_core/ot_a0_icg_hop.sv rtl/lib/ot_rst_relay.sv rtl/physical/ot_qwen_tile_operand.sv rtl/physical/ot_qwen_tile_rqr_half.sv
  physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
DEF=(+define+OT_QWEN_LSL_FP1)
[[ $TILE == nl ]] && DEF+=(+define+TB_NL)
DEF+=(+define+TB_ICG=${ICG:-1})   # QC-A0-KITS-13: ICG=2 build.sh ... = B-hop form
printf '%s\n' "${SRC[@]}" > "$OUT/files.txt"
sha256sum "${SRC[@]}" $D/tb_a0_icg.sv $D/*.sh > "$OUT/sources.sha256"
"$V" --version > "$OUT/verilator.version"
python3 tools/qwen_romleaf/a0core/equiv/gen_rom.py "$OUT/rom" 48 > /dev/null
rm -rf "$OUT/obj"
/usr/bin/time -v "$V" --binary --timing -j "$JOBS" -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
  -Wno-MULTIDRIVEN "${DEF[@]}" --top-module tb_a0_icg -Mdir "$OUT/obj" $D/tb_a0_icg.sv "${SRC[@]}" > "$OUT/build.log" 2>&1
echo "BUILD_OK $OUT/obj/Vtb_a0_icg"
