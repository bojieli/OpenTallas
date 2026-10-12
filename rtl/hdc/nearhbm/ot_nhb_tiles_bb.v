// el1011-q-kvd 2026-10-11: blackbox views of the hardened attention-hub tiles (ot_nhb_tiles.sv) for the hub cluster route.
(* blackbox *)
module ot_nhb_pbst (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         pv,
    input  wire         pgi,
    input  wire [5:0]   pbeat,
    input  wire [511:0] pdata,
    input  wire [5:0]   ra,
    output wire  [511:0] sr
);
endmodule
(* blackbox *)
module ot_nhb_pvlg (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [127:0] s0, s1, s2, s3,
    input  wire [31:0]  rz,
    output wire  [127:0] y,
    output wire  [3:0]   pf
);
endmodule
(* blackbox *)
module ot_nhb_zh (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire [127:0] zs_we,
    input  wire [127:0] sid,
    input  wire [3:0]   ziv,
    input  wire         zg,
    input  wire [5:0]   zp,
    output wire  [63:0]  root,
    output wire  [3:0]   zerr
);
endmodule
