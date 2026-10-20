#!/usr/bin/env bash
set -euo pipefail
G=$(cd "${1:?graph output directory}" && pwd)
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
O=$G/formal
mkdir -p "$O"
cat > "$O/miter.sv" <<'SV'
module svc7_graph_miter(input clk,rst_n,v,input [31:0] a,b,output bad);
  wire [31:0] x,y;
  wire [1:0] xe,ye;
  wire xv,yv;
  ot_s81svc7_add_graph_input original(.clk(clk),.rst_n(rst_n),.valid_in(v),
     .a(a),.b(b),.y(x),.err(xe),.valid_out(xv));
  ot_s81svc7_add_native candidate(.clk(clk),.rst_n(rst_n),.valid_in(v),
     .a(a),.b(b),.y(y),.err(ye),.valid_out(yv));
  // No in-flight reset mask: compare validity every edge and data on validity.
  assign bad=(xv!=yv) | ((xv|yv) & ({xe,x}!={ye,y}));
endmodule
SV
cat > "$O/proof.ys" <<'YS'
read_verilog -formal -sv /graph/native.v /graph/verify/cells.v /out/miter.sv /src/rtl/hdc/v41x/ot_s81svc7_add_graph_input.sv /src/rtl/hdc/ot_hdc_fp32_f12.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/rtl/hdc/ot_hdc_prefix.sv
hierarchy -check -top svc7_graph_miter
proc
flatten
opt_clean
async2sync
dffunmap
opt_clean
# No set-init-* options: every initial state bit, including every clone, free.
# The only skipped window is the specified initial two-stage reset landing.
# After step3 reset is an unconstrained input; no reset assumption/mask remains.
sat -seq 14 -set-def-inputs -set clk 1 -set-at 1 rst_n 0 -set-at 2 rst_n 0 -set-at 3 rst_n 0 -prove bad 0 -prove-skip 3 -verify -show-inputs -show-outputs
YS
docker run --rm -v "$ROOT:/src:ro" -v "$G:/graph:ro" -v "$O:/out" \
    openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -l /out/proof.log -s /out/proof.ys' > "$O/proof.stdout" 2>&1
tail -n 15 "$O/proof.log"
