#!/usr/bin/env bash
# run_land_eq.sh OUTDIR [none|NOAHEAD|NOWHIT] [SEED]  (cwd = repo root, Verilator 5.050) -> LAND_EQ PASS / FAIL
set -u; O=$(realpath -m "${1:?outdir}"); M=${2:-none}; S=${3:-1}; mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ "$M" != none ] && D="+define+OT_SRAM_LAND_MUT_$M"
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style $D --top-module tb_showahead_land -Mdir $O/obj_$M \
  rtl/lib/ot_sram_showahead_1r1w.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
  tools/s81_dv/lepmuh_c13_1022/tb_showahead_land.sv > $O/build_$M.log 2>&1 || { grep -m5 %Error $O/build_$M.log; echo BUILD_FAILED; exit 3; }
$O/obj_$M/Vtb_showahead_land +verilator+seed+$S > $O/run_${M}_$S.log 2>&1; grep -E "^(MISMATCH|LAND_)" $O/run_${M}_$S.log | head -8
grep -q "^LAND_EQ PASS" $O/run_${M}_$S.log
