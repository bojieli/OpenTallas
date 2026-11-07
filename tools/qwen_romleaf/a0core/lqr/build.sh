#!/bin/bash
# QC-A0C-B5 vB LQR bench build.  usage: build.sh TILE(nl|nk) KIT_RTL_DIR OUTDIR LQR [MUT] [JOBS]   (run from the repo root)
# OLD=<original kit rtl dir> (env): default-off proof, the ref side is that rtl preprocessed + prefixed K_ (LQR must be 0).
# KIT_RTL_DIR = a kit's rtl/ after lqr_patch.py; its black boxes (*_bb.v, the rawcut lsl netlist) are replaced by the
# behavioural models (romleaf, lsl_fp1 via OT_QWEN_LSL_FP1, node, ROM / SRAM macros); ROM images from equiv/gen_rom.py.
set -euo pipefail
TILE=$1; KR=$(realpath "$2"); OUT=$(mkdir -p "$3" && realpath "$3"); LQR=$4; MUT=${5:-0}; JOBS=${6:-16}
D=tools/qwen_romleaf/a0core/lqr
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
SRC=()
for f in "$KR"/*.sv "$KR"/*.v; do
  case $(basename "$f") in *_bb.v|ot_qwen_tile_lsl_rawcut.v) ;; *) SRC+=("$f");; esac
done
SRC+=(rtl/physical/ot_qwen_tile_romleaf.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv rtl/physical/ot_qwen_tile_node.sv
  "$OUT/models/ot_rom_4096x266_m8.v" "$OUT/models/ot_sram_1r1w_128x256_m1_r2c2.v")
mkdir -p "$OUT/models"
for m in ot_rom_4096x266_m8 ot_sram_1r1w_128x256_m1_r2c2; do
  git show origin/main:physical/asap7_memory_macros/$m/$m.v > "$OUT/models/$m.v"
done
DEF=(+define+OT_QWEN_LSL_FP1 +define+OT_ROM_CONST0_KV +define+TB_LQR=$LQR)
[[ $TILE == nl ]] && DEF+=(+define+TB_NL)
[[ $TILE == nk ]] && DEF+=(+define+OT_A0_LOCAL_OUT_RESET)
[[ $MUT != 0 ]] && DEF+=(+define+OT_LQR_MUT=$MUT)
# vB2: FSHIFT (env) = declared fault-bit shift (LQR bit3), FINJ (env) = fault injection time in ns (lqr2_patch.py)
[[ -n ${FSHIFT:-} ]] && DEF+=(+define+TB_FSHIFT=$FSHIFT)
[[ -n ${FINJ:-} ]] && DEF+=(+define+OT_LQR_FINJ=$FINJ)
EXTRA=()
if [[ -n ${OLD:-} ]]; then
  OSRC=()
  for f in "$(realpath "$OLD")"/*.sv "$(realpath "$OLD")"/*.v; do
    case $(basename "$f") in *_bb.v|ot_qwen_tile_lsl_rawcut.v) ;; *) OSRC+=("$f");; esac
  done
  OSRC+=("${SRC[@]: -5}")
  "$V" -E -P "${DEF[@]}" "${OSRC[@]}" > "$OUT/old_pp.sv"
  python3 -I tools/qwen_romleaf/a0core/equiv/rename.py "$OUT/old_pp.sv" "$OUT/old_k.sv" K_ 2> "$OUT/rename.log"
  DEF+=(+define+TB_OLD); EXTRA=("$OUT/old_k.sv")
  printf '%s\n' "${OSRC[@]}" > "$OUT/old_files.txt"
fi
printf '%s\n' "${SRC[@]}" > "$OUT/files.txt"
sha256sum "${SRC[@]}" $D/tb_a0_lqr.sv $D/*.sh $D/*.py > "$OUT/sources.sha256"
"$V" --version > "$OUT/verilator.version"
python3 -I tools/qwen_romleaf/a0core/equiv/gen_rom.py "$OUT/rom" 48 > /dev/null
rm -rf "$OUT/obj"
/usr/bin/time -v "$V" --binary --timing -j "$JOBS" -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
  -Wno-MULTIDRIVEN "${DEF[@]}" --top-module tb_a0_lqr -Mdir "$OUT/obj" $D/tb_a0_lqr.sv "${SRC[@]}" "${EXTRA[@]}" > "$OUT/build.log" 2>&1
echo "BUILD_OK $OUT/obj/Vtb_a0_lqr"
