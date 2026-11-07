#!/bin/bash
# QC-NLNK-RF2 vR bench build.  usage: rstp_build.sh TILE(nl|nk) KIT_RTL_DIR OUTDIR RSTP [MUT] [JOBS]  (repo root)
# OLD=<original kit rtl> (env, RSTP must be 0): default-off proof; ref = that rtl preprocessed + prefixed K_.
# Same behavioural models and ROM images as lqr/build.sh.
set -euo pipefail
TILE=$1; KR=$(realpath "$2"); OUT=$(mkdir -p "$3" && realpath "$3"); RSTP=$4; MUT=${5:-0}; JOBS=${6:-16}
D=tools/qwen_romleaf/a0core/lqr
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
LQR=25; [[ $TILE == nk ]] && LQR=31
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
PINC=${PINC:-0}
DEF=(+define+OT_QWEN_LSL_FP1 +define+OT_ROM_CONST0_KV +define+TB_LQR=$LQR +define+TB_RSTP=$RSTP +define+TB_FSHIFT=$PINC +define+OT_LQR_FINJ=${FINJ:-1650.2} +define+TB_PINC=$PINC)
[[ -n ${DRAIN:-} ]] && DEF+=(+define+TB_DRAIN=$DRAIN)
[[ $PINC != 0 ]] && DEF+=(+define+TB_PINC_ON)
[[ -n ${PMUT:-} ]] && DEF+=(+define+OT_PINC_MUT=$PMUT)
[[ $RSTP != 0 ]] && DEF+=(+define+TB_RSTP_ON)
[[ $TILE == nl ]] && DEF+=(+define+TB_NL)
[[ $TILE == nk ]] && DEF+=(+define+OT_A0_LOCAL_OUT_RESET)
[[ $MUT != 0 ]] && DEF+=(+define+OT_RSTP_MUT=$MUT)
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
fi
sha256sum "${SRC[@]}" $D/tb_a0_rstp.sv $D/rstp_*.sh $D/rstp_patch.py > "$OUT/sources.sha256"
python3 -I tools/qwen_romleaf/a0core/equiv/gen_rom.py "$OUT/rom" 48 > /dev/null
rm -rf "$OUT/obj"
"$V" --binary --timing -j "$JOBS" -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
  -Wno-MULTIDRIVEN "${DEF[@]}" --top-module tb_a0_rstp -Mdir "$OUT/obj" $D/tb_a0_rstp.sv "${SRC[@]}" "${EXTRA[@]}" > "$OUT/build.log" 2>&1
echo "BUILD_OK $OUT/obj/Vtb_a0_rstp"
