#!/usr/bin/env bash
set -euo pipefail
G=$(cd "${1:?graph output directory}" && pwd)
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
O=$G/formal
mkdir -p "$O"
cat > "$O/miter.sv" <<'SV'
module svc7_graph_miter(input clk,rst_n,pad,input [15:0] a,b,output bad);
 wire [31:0] x,y; wire xf,yf;
 ot_s81svc7_bmul_graph_input original(.clk(clk),.rst_n(rst_n),.pad(pad),.a(a),.b(b),.y(x),.flt(xf));
 ot_s81svc7_bmul_native candidate(.clk(clk),.rst_n(rst_n),.pad(pad),.a(a),.b(b),.y(y),.flt(yf));
 // No validity/reset mask. Compare every output after initial pipeline flush.
 assign bad=({xf,x}!={yf,y});
endmodule
SV
cat > "$O/proof.ys" <<'YS'
read_verilog -formal -sv /graph/native.v /graph/verify/cells.v /out/miter.sv /src/rtl/hdc/v41x/ot_s81svc7_bmul_graph_input.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv /src/rtl/hdc/ot_hdc_prefix.sv
hierarchy -check -top svc7_graph_miter
proc
flatten
opt_clean
async2sync
dffunmap
opt_clean
# No set-init-* options: every initial state bit, including every clone, free.
# Skip nine initial edges: two reset landing + seven arithmetic edges.
# After step3 reset is unconstrained; all data and fault outputs compared even during in-flight reset.
sat -seq 18 -set-def-inputs -set clk 1 -set-at 1 rst_n 0 -set-at 2 rst_n 0 -set-at 3 rst_n 0 -prove bad 0 -prove-skip 9 -verify -show-inputs -show-outputs
YS
docker run --rm -v "$ROOT:/src:ro" -v "$G:/graph:ro" -v "$O:/out" \
    openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -l /out/proof.log -s /out/proof.ys' > "$O/proof.stdout" 2>&1
tail -n 15 "$O/proof.log"
