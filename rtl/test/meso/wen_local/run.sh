#!/bin/bash
# WEN-LOCAL-1 lock-step bench: A = cas WREG=1 WEN_LOCAL=1 == plain ring behind one t_rst_n flop, every clk edge, random phases,
# START low between cases; rising / WFALL / WFALL+FREG forms, WRITE_CHUNK 16 and 64; mutant WENLOC caught.  usage: run.sh OUT
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd); OUT=${1:?output directory}; mkdir -p "$OUT"; rc=0
V=(verilator --binary --timing --build -j 8 --top-module tb -Wno-fatal -Wno-lint -Wno-style)
S=("$R/rtl/test/meso/wen_local/tb_wen_local.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv")
one() { # tag expect defs
  local t=$1 e=$2; shift 2
  "${V[@]}" "$@" --Mdir "$OUT/$t" "${S[@]}" > "$OUT/$t.build.log" 2>&1 || { echo "BUILD_FAIL $t"; tail -3 "$OUT/$t.build.log"; rc=1; return; }
  "$OUT/$t/Vtb" +seed=7 +n=300 > "$OUT/$t.log" 2>&1
  local l; l=$(grep WREG_EQUIV "$OUT/$t.log"); echo "$t expect $e: $l"
  case "$e" in
    SAME) [ "$l" = "$(grep WREG_EQUIV "$OUT/base_$t.log")" ] || rc=1;;
    *) case "$l" in *$e) ;; *) rc=1;; esac;;
  esac
}
# The rising-form bench of the reference tb reports A/B mismatches before ready on the UNCHANGED ring too (tb clocking of B's
# start flop, not the ring): there the WEN_LOCAL ring must give the IDENTICAL WREG_EQUIV line as the reference WREG ring.
base() { local t=$1; shift
  "${V[@]}" "$@" --Mdir "$OUT/base_$t" "$R/results/dh58_turnb_1103/wreg_equiv/tb_wreg_equiv.sv" "${S[@]:1}" > "$OUT/base_$t.build.log" 2>&1 || { echo "BUILD_FAIL base_$t"; rc=1; return; }
  "$OUT/base_$t/Vtb" +seed=7 +n=300 > "$OUT/base_$t.log" 2>&1; }
base rise16; cp "$OUT/base_rise16.log" "$OUT/base_rise64.log"
one rise16 SAME
one rise64 SAME +define+WCHUNK=64
one wfall16 PASS +define+TB_WFALL
one wfall_freg16 PASS +define+TB_WFALL +define+TB_FREG
one mut_rise16 FAIL +define+OT_MESO_CA_MUTANT_WENLOC
one mut_wfall16 FAIL +define+TB_WFALL +define+OT_MESO_CA_MUTANT_WENLOC
echo "RC $rc"; exit $rc
