#!/usr/bin/env bash
# S81-L20DIE (10-19): dsdv_idx_qf bench (tb_dsdv_idx_qf), MUT 0 must PASS, MUT 1 (next uid's spec) and MUT 2 (NAT32 slice-15 qs mask stuck 0, TOK-FUNC2-IDX_QF 10-21) must FAIL.
# S81/PORTFIX-CFG 10-25: + MUT 3 (config frame leaks to qr / qc), 4 (uid nibbles swapped at the load), 5 (no-entry dropped
# from the fault fold) and BS_MUT 2 (dsdv_idx_bsplit keeps type 11 on the svc output) must FAIL.
# Run from the source root on a fleet host (Verilator 5.050).  usage: run_idx_qf.sh OUT
set -u
O=$1; mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_bsplit.sv rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_qf.sv"
( sha256sum $SRC; $VL --version ) > "$O/sources.sha256"
bad=0
for c in m0:0:0 m1:1:0 m2:2:0 m3:3:0 m4:4:0 m5:5:0 b2:0:2; do
  IFS=: read n m b <<< "$c"
  $VL --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -GMUT=$m -GBS_MUT=$b --top-module tb_dsdv_idx_qf $SRC --Mdir "$O/obj_$n" > "$O/build_$n.log" 2>&1 \
    || { echo "QF BUILD FAIL $n"; tail -5 "$O/build_$n.log"; exit 2; }
  "$O/obj_$n/Vtb_dsdv_idx_qf" > "$O/run_$n.log" 2>&1
  v=$(grep -E '^TB_QF (PASS|FAIL)$' "$O/run_$n.log" | tail -1)
  want=$([ $n = m0 ] && echo "TB_QF PASS" || echo "TB_QF FAIL")
  [ "$v" = "$want" ] && echo "QF_CASE OK $n: $v" || { echo "QF_CASE BAD $n: $v"; bad=1; }
done
[ $bad = 0 ] && echo "QF_BENCH PASS" || echo "QF_BENCH FAIL"; exit $bad
