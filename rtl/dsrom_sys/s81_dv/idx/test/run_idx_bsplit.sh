#!/usr/bin/env bash
# DRIVE-S81-IDX4 (10-20): dsdv_idx_bsplit bench (tb_dsdv_idx_bsplit), MUT 0 must PASS, MUT 1 (type 10 kept on svc) must FAIL.
# Run from the source root on a fleet host (Verilator 5.050).  usage: run_idx_bsplit.sh OUT
set -u
O=$1; mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="rtl/dsrom_sys/s81_dv/idx/dsdv_idx_bsplit.sv rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_bsplit.sv"
( sha256sum $SRC; $VL --version ) > "$O/sources.sha256"
bad=0
for m in 0 1; do
  $VL --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -GMUT=$m --top-module tb_dsdv_idx_bsplit $SRC --Mdir "$O/obj_m$m" > "$O/build_m$m.log" 2>&1 \
    || { echo "BS BUILD FAIL m$m"; tail -5 "$O/build_m$m.log"; exit 2; }
  "$O/obj_m$m/Vtb_dsdv_idx_bsplit" > "$O/run_m$m.log" 2>&1
  v=$(grep -E '^TB_BS (PASS|FAIL)$' "$O/run_m$m.log" | tail -1)
  want=$([ $m = 0 ] && echo "TB_BS PASS" || echo "TB_BS FAIL")
  [ "$v" = "$want" ] && echo "BS_CASE OK m$m: $v" || { echo "BS_CASE BAD m$m: $v"; bad=1; }
done
[ $bad = 0 ] && echo "BS_BENCH PASS" || echo "BS_BENCH FAIL"; exit $bad
