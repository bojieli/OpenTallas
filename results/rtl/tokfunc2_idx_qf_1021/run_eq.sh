#!/usr/bin/env bash
# TOK-FUNC2-IDX_QF 10-21: lockstep equivalence dsdv_idx_qf (rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv) vs the G8IQ blob
# c31c5c582 (old_dsdv_idx_qf_c31c5c582.sv), seeds 1..6.  usage: run_eq.sh OUT [MUT]  (MUT 2 must FAIL)
set -u
O=$1; M=${2:-0}; mkdir -p "$O"
D=results/rtl/tokfunc2_idx_qf_1021
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="$D/old_dsdv_idx_qf_c31c5c582.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv $D/tb_dsdv_idx_qf_eq.sv"
( sha256sum $SRC; $VL --version ) > "$O/sources.sha256"
$VL --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -GMUT=$M --top-module tb_eq $SRC --Mdir "$O/obj" > "$O/build.log" 2>&1 \
  || { echo "QF_EQ BUILD FAIL"; tail -5 "$O/build.log"; exit 2; }
bad=0
for s in 1 2 3 4 5 6; do
  "$O/obj/Vtb_eq" +seed=$s > "$O/run_s$s.log" 2>&1
  l=$(grep -E '^EQ_STATS' "$O/run_s$s.log"); echo "$l"
  grep -qE '^EQ PASS$' "$O/run_s$s.log" || bad=$((bad + 1))
done
[ $bad = 0 ] && echo "QF_EQ PASS seeds 6" || echo "QF_EQ FAIL seeds_bad $bad MUT $M"; exit $bad
