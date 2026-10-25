#!/usr/bin/env bash
# S81/PORTFIX-CFG 10-25: dsdv_eng_cfg unit bench (tb_dsdv_eng_cfg).  MUT 0 must PASS; MUT 1 (rank bits swapped), 2 (decode
# on kind only), 3 (no XQ / XB continuation tracking), 4 (st[2] dropped from the fault fold), 5 (en reset 1) must FAIL.
# Run from the source root on a fleet host (Verilator 5.050).  usage: run_eng_cfg.sh OUT
set -u
O=$1; mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
# dsdv_eng_cfg is defined in dsdv_eng_rr.sv: the bench takes that module alone (extracted verbatim; the file's other
# modules need the whole Engram source list)
awk '/^module dsdv_eng_cfg /,/^endmodule/' rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr.sv > "$O/dsdv_eng_cfg_only.sv"
SRC="rtl/lib/ot_rst_relay.sv $O/dsdv_eng_cfg_only.sv rtl/dsrom_sys/s81_dv/eng/test/tb_dsdv_eng_cfg.sv"
( sha256sum rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr.sv $SRC; $VL --version ) > "$O/sources.sha256"
bad=0
for m in 0 1 2 3 4 5; do
  $VL --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-PINMISSING -Wno-IMPLICIT -GMUT=$m --top-module tb_dsdv_eng_cfg $SRC \
      --Mdir "$O/obj_m$m" > "$O/build_m$m.log" 2>&1 || { echo "ENG_CFG BUILD FAIL m$m"; tail -5 "$O/build_m$m.log"; exit 2; }
  "$O/obj_m$m/Vtb_dsdv_eng_cfg" > "$O/run_m$m.log" 2>&1
  v=$(grep -E '^TB_ENG_CFG (PASS|FAIL)$' "$O/run_m$m.log" | tail -1)
  want=$([ $m = 0 ] && echo "TB_ENG_CFG PASS" || echo "TB_ENG_CFG FAIL")
  [ "$v" = "$want" ] && echo "ENG_CFG_CASE OK m$m: $v" || { echo "ENG_CFG_CASE BAD m$m: $v"; bad=1; }
done
[ $bad = 0 ] && echo "ENG_CFG_BENCH PASS" || echo "ENG_CFG_BENCH FAIL"; exit $bad
