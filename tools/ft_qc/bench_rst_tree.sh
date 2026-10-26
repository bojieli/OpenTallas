#!/bin/bash
# FT-QC: equal-release-age bench of a generated in-cluster reset tree (every region releases on the same edge,
# 1 landing + D chain flops after rst_n) + a one-stage-short mutant (last region, stage 1 bypassed) that must FAIL.
# usage: bench_rst_tree.sh [CF_SV]   (default: the CB8 pilot rtl/physical/qcluster/qfd_c_b8_ft_cf.sv; works for CB16)
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); CF=${1:-$R/rtl/physical/qcluster/qfd_c_b8_ft_cf.sv}; T=$(mktemp -d)
python3 -I - "$CF" "$T" <<'PY'
import re, sys
cf, T = sys.argv[1], sys.argv[2]
s = open(cf).read()
m = re.search(r'^module (\w+_rst_tree) \((.*?)^endmodule', s, re.S | re.M)
mod, body = m.group(1), m.group(0)
regs = re.findall(r'output wire rst_(c\dr\d)', body)
D = len(re.findall(rf'u_{regs[0]}_\d+ ', body))
open(f'{T}/tree.sv', 'w').write(body + '\n')
q = regs[-1]
mut, n = re.subn(rf'\.d\(r_{q}_0\), \.q\(r_{q}_1\)\);', f'.d(r_{q}_0), .q());\n    assign r_{q}_1 = r_{q}_0;', body)
assert n == 1
open(f'{T}/mut.sv', 'w').write(mut + '\n')
N = len(regs)
conn = ', '.join(f'.ck_{r}(ck)' for r in regs) + ', ' + ', '.join(f'.rst_{r}(r[{i}])' for i, r in enumerate(regs))
open(f'{T}/tb.sv', 'w').write(f'''`timescale 1ns/1ps
module tb;
  reg ck = 0; always #1 ck = ~ck;
  reg rst_n = 0; wire [{N-1}:0] r;
  {mod} u (.rst_n(rst_n), {conn});
  integer e = 0, t0 = -1, fail = 0, k;
  always @(posedge ck) begin
    e <= e + 1; if (e == 40) rst_n <= 1;
    for (k = 0; k < {N}; k = k + 1) if (r[k] !== r[0]) fail = 1;
    if (r[0] === 1'b1 && t0 < 0) t0 = e;
  end
  // expected edges = 1 landing + D={D} chain flops + 1 sampling edge of this monitor
  initial begin repeat ({D + 80}) @(posedge ck);
    $display("RELEASE regions={N} all_equal=%0d edges=%0d", !fail, t0 - 40);
    if (fail || t0 - 40 != {D + 2}) $display("FAIL"); else $display("PASS"); $finish; end
endmodule
''')
PY
iverilog -g2012 -o $T/a $T/tb.sv $T/tree.sv $R/rtl/physical/qcluster/qfd_q3h_stn.sv
iverilog -g2012 -o $T/m $T/tb.sv $T/mut.sv $R/rtl/physical/qcluster/qfd_q3h_stn.sv
A=$(vvp -n $T/a | tail -1); M=$(vvp -n $T/m | tail -1); echo "$(vvp -n $T/a | tail -2 | head -1)  positive: $A  mutant: $M"; rm -rf $T
[ "$A" = PASS ] && [ "$M" = FAIL ]
