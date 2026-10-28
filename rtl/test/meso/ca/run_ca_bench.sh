#!/bin/bash
# MESO-COUNT-1 Verilator benches for ot_dp_clk_landing_ca.  Usage: run_ca_bench.sh OUT [CASES.tsv ...]
# Runs: (1) lag sweeps K in {-2,1,2,5} x DEPTH {4,8} over L = -(2 DEPTH + 1) T .. +(2 DEPTH + 1) T at 1 ps
#     (clean window must be [0.5, DEPTH-0.5] T, 0 silent-wrong anywhere, incl. the 1-bit-lap alias at L - 2 DEPTH T);
#     mutants (must FAIL = silent-wrong > 0): NO_TAG (extended lap tag ignored), K (reader one count late);
# (2) tree crossing (origin from the forwarded start) phase sweep, rise and fall sample edge;
# (3) every case file (id depth L_ps) at DEPTH 4 and 8 builds.
set -eu
here=$(cd "$(dirname "$0")" && pwd); repo=$(git -C "$here" rev-parse --show-toplevel)
out=${1:?usage: run_ca_bench.sh OUT [CASES...]}; shift
mkdir -p "$out"; cd "$out"
cp "$repo"/rtl/common/{ot_meso_fifo.sv,ot_dp_clk_landing.sv,ot_dp_clk_landing_ca.sv} "$here"/tb_dp_clk_landing_ca.{sv,cpp} "$here"/tb_ca_tree.{sv,cpp} .
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
V="verilator --cc --exe --build -j 8 -Wno-fatal -Wno-lint"
rc=0
for D in 4 8; do for K in -2 1 2 5; do
  $V -CFLAGS "-DKPAR=$K -DDPAR=$D" -GK=$K -GDEPTH=$D --top-module tb_dp_clk_landing_ca tb_dp_clk_landing_ca.sv ot_dp_clk_landing_ca.sv ot_dp_clk_landing.sv ot_meso_fifo.sv tb_dp_clk_landing_ca.cpp --Mdir o_k${K}_d$D > b_k${K}_d$D.log 2>&1
  o_k${K}_d$D/Vtb_dp_clk_landing_ca sweep $(( -(2*D+1)*833 )) $(( (2*D+1)*833 )) 1 2>/dev/null || rc=1
done; done
for M in NO_TAG K; do
  $V -CFLAGS "-DKPAR=2 -DDPAR=4" -GK=2 -GDEPTH=4 -DOT_MESO_CA_MUTANT_$M --top-module tb_dp_clk_landing_ca tb_dp_clk_landing_ca.sv ot_dp_clk_landing_ca.sv ot_dp_clk_landing.sv ot_meso_fifo.sv tb_dp_clk_landing_ca.cpp --Mdir o_mut_$M > b_mut_$M.log 2>&1
  if o_mut_$M/Vtb_dp_clk_landing_ca sweep -7497 7497 1 2>/dev/null; then echo "MUTANT $M SURVIVED"; rc=1; else echo "MUTANT $M CAUGHT"; fi
done
for E in 0 1; do
  $V -CFLAGS "-DKPAR=-2" -GK=-2 -GEDGE_FALL=$E --top-module tb_ca_tree tb_ca_tree.sv ot_dp_clk_landing_ca.sv ot_dp_clk_landing.sv ot_meso_fifo.sv tb_ca_tree.cpp --Mdir o_tree$E > b_tree$E.log 2>&1
  echo -n "EDGE_FALL=$E "; o_tree$E/Vtb_ca_tree || rc=1
done
for c in "$@"; do for D in 4 8; do echo -n "$(basename $c) "; o_k2_d$D/Vtb_dp_clk_landing_ca "$c" | tail -1 || rc=1; done; done
exit $rc
