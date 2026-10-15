#!/bin/bash
# rxh_eq_gate.sh OUT [SEEDS] (S-ELEM-C 2026-10-15): the RX cluster ot_s81_su_rxh (v2) against the flat tile ot_s81_su_rxt
# (tb_s81_su_rxh_eq.sv), XMUT 0 on every seed (must PASS) and XMUT 1..5 (each leaf's negative control, must FAIL; 5 = RA front leaf drops the max(x,0) clamp, 6 = control QR row index stuck).
# XMUT 5 / 6 use explicitly mutated DUT-source copies: initial force was not observable in retained Verilator builds.
# Run from the repository root (via ot-run on a fleet host).  Writes OUT/receipt.json with the source hashes.
set -u
OUT=${1:?out dir}; SEEDS=${2:-"1 2 3 4"}; NJOB=${NJOB:-48}
mkdir -p "$OUT"  # XLIST (env) selects the variants
SRC="rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxt.sv rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv
 rtl/dsrom_sys/s81_suhc/ot_s81_su_rx.sv rtl/hdc/v41x/ot_hdc_v41x_spshort.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_delay.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv
 rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/dsrom_sys/s81_suhc/test/tb_s81_su_rxh_eq.sv"
sha256sum $SRC > "$OUT/sources.sha256"
rc_all=0; : > "$OUT/summary.txt"
for X in ${XLIST:-0 1 2 3 4 5 6 7}; do
  obj="$OUT/obj_x$X"
  XSRC="$SRC"
  if [ "$X" -ge 5 ]; then
    python3 tools/s81_suhc/rxh_mutant_source.py --mut "$X" --out "$OUT/mut_x$X.sv" || exit 1
    XSRC="${SRC/rtl\/dsrom_sys\/s81_suhc\/hier\/ot_s81_su_rxh.sv/$OUT/mut_x$X.sv}"
  fi
  verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_s81_su_rxh_eq -Mdir "$obj" -j 16 \
      -GXMUT=$X -GNJOB=$NJOB $XSRC > "$OUT/build_x$X.log" 2>&1 || { echo "BUILD FAIL x$X" | tee -a "$OUT/summary.txt"; rc_all=1; continue; }
  if [ $X -eq 0 ]; then ss="$SEEDS"; else ss="1"; fi
  for S in $ss; do
    "$obj/Vtb_s81_su_rxh_eq" +SEED=$S > "$OUT/run_x${X}_s$S.log" 2>&1
    res=$(grep -E "RXH_EQ (PASS|FAIL)" "$OUT/run_x${X}_s$S.log" | tail -1)
    shadow=$(grep -c RXC_SHADOW_FAIL "$OUT/run_x${X}_s$S.log")
    echo "x$X s$S $res shadow_fail=$shadow" | tee -a "$OUT/summary.txt"
    grep "RXH_EQ kind\|RXH_EQ rows" "$OUT/run_x${X}_s$S.log" | sed "s/^/  /" >> "$OUT/summary.txt"
    if [ $X -eq 0 ] && { [ "$res" != "RXH_EQ PASS" ] || [ "$shadow" != 0 ]; }; then rc_all=1; fi
    if [ $X -ne 0 ] && [ -z "${RAW:-}" ] && [ "$res" != "RXH_EQ FAIL" ]; then rc_all=1; fi
    if [ -n "${RAW:-}" ] && [ "$res" != "RXH_EQ PASS" ]; then rc_all=1; fi   # RAW: exit 0 iff every run PASSes (closure-loop expect pass / fail)
  done
  rm -rf "$obj"
done
echo "GATE rc=$rc_all" | tee -a "$OUT/summary.txt"
exit $rc_all
