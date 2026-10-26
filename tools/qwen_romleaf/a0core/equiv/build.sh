#!/bin/bash
# A0 bound-vs-kit port equivalence: build one bench.
# usage: build.sh TILE(nk|nl) BVAR(asbound|fp1) OUTDIR [JOBS]
#   BOUND side (bound_r8 binder closure; main-tree qfd_tile_<t>_rp2_romleaf_rr.sv + qfd_tile_<t>_rp2_45.sv, REGROOT 2),
#     preprocessed with the binder's defines (asbound: OT_QFD_UP4_CK_ENTRIES only, as physical/die_plan/qwen_compute/bind/
#     asbuilt_tie.json records -> ot_qwen_tile_lsl; fp1: + OT_QWEN_LSL_FP1 -> ot_qwen_tile_lsl_fp1).
#   KIT side (physical/ref_tile/qfd_tile_<t>_a0cv6/kit.env SRCS, black boxes replaced by the behavioural models),
#     preprocessed with the kit defines (OT_QWEN_LSL_FP1, OT_A0_CK_TAPS*), then every module it defines prefixed K_.
# Run from the repo root (or set R).  Writes OUTDIR/{bound_pp.sv,kit_pp.sv,kit_k.sv,tb.sv,obj/,build.log}.
set -euo pipefail
TILE=$1; BVAR=$2; OUT=$(mkdir -p "$3" && realpath "$3"); JOBS=${4:-16}
R=${R:-$(cd "$(dirname "$0")/../../../.." && pwd)}
cd "$R"
E=tools/qwen_romleaf/a0core/equiv
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}

BOUND=(rtl/lib/ot_reset_sync.sv rtl/physical/qfd_tile_${TILE}_rp2_romleaf_rr.sv rtl/physical/qfd_tile_${TILE}_rp2_45.sv
  rtl/physical/ot_qwen_rom_tile_nk.sv rtl/hdc/ot_qwen_rom_tile_w12.sv
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
  physical/asap7_memory_macros_v2/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
  rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv rtl/hdc/ot_qwen_w12_arith.sv
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
  rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tile_operand.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv
  rtl/physical/ot_qwen_tile_lsl.sv rtl/physical/ot_qwen_tile_rqr_half.sv rtl/physical/ot_qwen_tile_rpair.sv
  rtl/physical/ot_qwen_tile_romleaf.sv rtl/physical/ot_qwen_tile_node.sv rtl/lib/ot_rst_relay.sv
  rtl/hdc/ot_qwen_me_array_w12.sv rtl/lib/ot_rst_pipe.sv)
BDEF=(+define+OT_QFD_UP4_CK_ENTRIES)
[[ $BVAR == fp1 ]] && BDEF+=(+define+OT_QWEN_LSL_FP1)
[[ $BVAR == asbound || $BVAR == fp1 ]] || { echo "BVAR asbound|fp1"; exit 2; }

KIT_DIR=physical/ref_tile/qfd_tile_${TILE}_a0cv6
eval "$(grep '^SRCS=' $KIT_DIR/kit.env)"
KIT=()
for f in $SRCS; do [[ $f == *_bb.v ]] || KIT+=("$f"); done
KIT+=(rtl/physical/ot_qwen_tile_romleaf.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv rtl/physical/ot_qwen_tile_node.sv
  rtl/lib/ot_rst_relay.sv rtl/physical/ot_qwen_tile_operand.sv rtl/physical/ot_qwen_tile_rqr_half.sv
  physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
KDEF=(+define+OT_QWEN_LSL_FP1 +define+OT_A0_CK_TAPS +define+OT_A0_CK_TAPS24 +define+OT_A0_CK_TAPS31)
[[ $TILE == nk ]] && KDEF+=(+define+OT_A0_CK_TAPS32)

printf '%s\n' "${BOUND[@]}" > "$OUT/bound_files.txt"
printf '%s\n' "${KIT[@]}" > "$OUT/kit_files.txt"
sha256sum "${BOUND[@]}" "${KIT[@]}" $E/*.py $E/*.sh > "$OUT/sources.sha256"
"$V" --version > "$OUT/verilator.version"
"$V" -E -P "${BDEF[@]}" "${BOUND[@]}" > "$OUT/bound_pp.sv"
"$V" -E -P "${KDEF[@]}" "${KIT[@]}" > "$OUT/kit_pp.sv"
python3 $E/rename.py "$OUT/kit_pp.sv" "$OUT/kit_k.sv" K_ 2> "$OUT/rename.log"
python3 $E/gen_tb.py "$TILE" "$OUT/bound_pp.sv" qfd_tile_${TILE}_rp2_romleaf_rr "$OUT/kit_k.sv" K_qfd_tile_${TILE}_a0c 48 "$OUT/tb.sv"
python3 $E/gen_rom.py "$OUT/rom" 48 > /dev/null
rm -rf "$OUT/obj"
/usr/bin/time -v "$V" --binary --timing -j "$JOBS" -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
  -Wno-MULTIDRIVEN --top-module tb_a0_equiv -Mdir "$OUT/obj" "$OUT/tb.sv" "$OUT/bound_pp.sv" "$OUT/kit_k.sv" \
  > "$OUT/build.log" 2>&1
echo "BUILD_OK $OUT/obj/Vtb_a0_equiv"
