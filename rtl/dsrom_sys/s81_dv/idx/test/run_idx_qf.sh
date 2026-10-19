#!/usr/bin/env bash
# S81-L20DIE (10-19): dsdv_idx_qf bench (tb_dsdv_idx_qf), MUT 0 must PASS, MUT 1 (next uid's spec) must FAIL.
# Run from the source root on a fleet host (Verilator 5.050).  usage: run_idx_qf.sh OUT
set -u
O=$1; mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_qf.sv"
( sha256sum $SRC; $VL --version ) > "$O/sources.sha256"
bad=0
for m in 0 1; do
  $VL --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -GMUT=$m --top-module tb_dsdv_idx_qf $SRC --Mdir "$O/obj_m$m" > "$O/build_m$m.log" 2>&1 \
    || { echo "QF BUILD FAIL m$m"; tail -5 "$O/build_m$m.log"; exit 2; }
  "$O/obj_m$m/Vtb_dsdv_idx_qf" > "$O/run_m$m.log" 2>&1
  v=$(grep -E '^TB_QF (PASS|FAIL)$' "$O/run_m$m.log" | tail -1)
  want=$([ $m = 0 ] && echo "TB_QF PASS" || echo "TB_QF FAIL")
  [ "$v" = "$want" ] && echo "QF_CASE OK m$m: $v" || { echo "QF_CASE BAD m$m: $v"; bad=1; }
done
[ $bad = 0 ] && echo "QF_BENCH PASS" || echo "QF_BENCH FAIL"; exit $bad
