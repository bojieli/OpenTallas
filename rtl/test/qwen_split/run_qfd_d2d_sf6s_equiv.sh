#!/usr/bin/env bash
# QW-D2D SAFE5 10-19: lockstep equivalence bench qfd_d2d_static_ovl_sf vs qfd_d2d_static_ovl (tb_qfd_d2d_sf6s_equiv.sv),
# Verilator 5.050 (the closure daemon's version).  Usage: run_qfd_d2d_sf_equiv.sh OUTDIR [SFMUT] [NCYC]
# Prints one line "sfeq_m<SFMUT> got=PASS|FAIL" plus the bench's SFEQ_ lines; exit 0 iff the bench ran to completion.
set -u
OUT=${1:?outdir}; MUTV=${2:-0}; NCYC=${3:-200000}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/d2d_static_20261015; S=rtl/qwen_sys/split_20261014
SRC=(rtl/lib/ot_rst_pipe.sv "$S/ot_qwen_crc_parallel.sv" "$S/ot_qwen_static_slot_link.sv" "$S/ot_qkvd_d2d_llr.sv"
     "$S/qkd_native_attention_record.sv" "$D/ot_qwen_d2d_static.sv" "$D/ot_qwen_d2d_services.sv" "$D/ot_qwen_d2d_dies.sv"
     "$D/ot_qwen_d2d_dies_ovl.sv" "$D/ot_qwen_d2d_safe5.sv" "$D/ot_qwen_d2d_dies_ovl_sf.sv" "$D/ot_qwen_d2d_safe6s.sv" "$D/ot_qwen_d2d_dies_ovl_sf6s.sv" rtl/qwen_split/qfd_kvn_static_transport.sv
     physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
     physical/asap7_memory_macros_v2/ot_sram_1r1w_64x137_m1_r2c2_p192/ot_sram_1r1w_64x137_m1_r2c2_p192.v
     rtl/test/qwen_split/tb_qfd_d2d_sf6s_equiv.sv)
mkdir -p "$OUT"
sha256sum "${SRC[@]}" "$0" > "$OUT/source.sha256"
"$V" --version > "$OUT/verilator.version"
"$V" --binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH \
     ${SFEQ_VFLAGS:-} --top-module tb_qfd_d2d_sf6s_equiv -GSFMUT="$MUTV" -GNCYC="$NCYC" --Mdir "$OUT/obj" "${SRC[@]}" > "$OUT/build.log" 2>&1 \
  || { echo "sfeq_m$MUTV got=BUILD_FAIL"; grep -m8 '%Error' "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_qfd_d2d_sf6s_equiv" > "$OUT/run.log" 2>&1
rm -rf "$OUT/obj"
got=FAIL; grep -q '^SFEQ_PASS' "$OUT/run.log" && got=PASS
echo "sfeq_m$MUTV got=$got"
grep -E '^SFEQ_|^    bit' "$OUT/run.log" | head -12
grep -qE '^SFEQ_(PASS|FAIL)' "$OUT/run.log"
