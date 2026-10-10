`timescale 1ps/1fs
`default_nettype none
// Opt-in full-shape T1 die endpoint; the historical core defaults stay intact.
// FWD=0 uses the production stream clock; qx is only a T4 column-tap output.
module hfd_idx_score_native (
 input wire ck, rst,
 input wire [8791:0] ik,
 output wire [7:0] ikc,
 input wire [570:0] q,
 output wire [609:0] s,
 input wire sc,
 output wire [3:0] st
);
 hfd_idx_score #(.L(16),.FA(6),.CRED(128),.FWD(0)) core (
  .ck(ck),.rst(rst),.ik(ik),.ikf(8'b0),.ikc(ikc),.q(q),.qx(),
  .s(s),.sc(sc),.st(st));
endmodule

// Parallel larger slot candidate uses identical full-shape functional hardware.
module hfd_idx_score_native_c2 (
 input wire ck, rst,
 input wire [8791:0] ik,
 output wire [7:0] ikc,
 input wire [570:0] q,
 output wire [609:0] s,
 input wire sc,
 output wire [3:0] st
);
 hfd_idx_score_native core (.*);
endmodule

// Mirror-grid successors preserve hardware; their abstracts add 24nm above
// the row-aligned cell core to preserve M4 track phase under MX/R180.
module hfd_idx_score_native_grid (
 input wire ck, rst, input wire [8791:0] ik, output wire [7:0] ikc,
 input wire [570:0] q, output wire [609:0] s, input wire sc,
 output wire [3:0] st
);
 hfd_idx_score_native core (.*);
endmodule
module hfd_idx_score_native_grid_c2 (
 input wire ck, rst, input wire [8791:0] ik, output wire [7:0] ikc,
 input wire [570:0] q, output wire [609:0] s, input wire sc,
 output wire [3:0] st
);
 hfd_idx_score_native core (.*);
endmodule
`default_nettype wire
