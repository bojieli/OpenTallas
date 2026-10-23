#!/bin/bash
# FT-QC: equal-release-age bench of the generated in-cluster reset tree (all 8 regions release on the same edge,
# 1 landing + D chain flops after rst_n) + a one-stage-short mutant that must FAIL.  usage: bench_rst_tree.sh [CF_SV]
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); CF=${1:-$R/rtl/physical/qcluster/qfd_c_b8_ft_cf.sv}; T=$(mktemp -d)
sed -n '/^module qfd_c_b8_ft_rst_tree/,/^endmodule/p' "$CF" > $T/tree.sv
sed -E 's/\.d\(r_c1r3_6\), \.q\(r_c1r3_7\)\);/.d(r_c1r3_6), .q());\n    assign r_c1r3_7 = r_c1r3_6;/' $T/tree.sv > $T/mut.sv
iverilog -g2012 -o $T/a $R/tools/ft_qc/tb_rst_tree.sv $T/tree.sv $R/rtl/physical/qcluster/qfd_q3h_stn.sv
iverilog -g2012 -o $T/m $R/tools/ft_qc/tb_rst_tree.sv $T/mut.sv $R/rtl/physical/qcluster/qfd_q3h_stn.sv
A=$(vvp -n $T/a | tail -1); M=$(vvp -n $T/m | tail -1)
echo "positive: $A  mutant: $M"; rm -rf $T
[ "$A" = PASS ] && [ "$M" = FAIL ]
