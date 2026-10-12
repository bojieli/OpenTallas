`default_nettype none
// Parameter-free hard-tile tops for the hfd_idx_sel_native_qend quarter cluster (el1011-hbm-idx, 10-12).
// Each wraps an UNCHANGED leaf of the V4.1x selector (rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv) at the
// parameters the qend instance uses, so the hard tile is the same logic as the flat RTL:
//   hfd_qsel_hist_k : topk slice histogram   (W=16, CB=11; K=512)   x2 per quarter (u_hc, u_hf)
//   hfd_qsel_hist_c : cand slice histogram   (W=2,  CB=13; K=2048)  x2 per quarter
//   hfd_qsel_pack_k : topk slice packer      (W=16, PW=37)          x2 per quarter (u_pi, u_ps)
module hfd_qsel_hist_k (
  input  wire clk, rst_n, clr, i_v,
  input  wire [15:0] i_en,
  input  wire [127:0] i_dg,
  input  wire [3:0] gsel,
  output wire [16*15-1:0] gsum,
  output wire [16*11-1:0] gbin,
  output wire busy
);
  ot_hdc_v41x_sel_hist #(.W(16), .CB(11)) u (.clk(clk), .rst_n(rst_n), .clr(clr), .i_v(i_v), .i_en(i_en),
    .i_dg(i_dg), .gsel(gsel), .gsum(gsum), .gbin(gbin), .busy(busy));
endmodule
module hfd_qsel_hist_c (
  input  wire clk, rst_n, clr, i_v,
  input  wire [1:0] i_en,
  input  wire [15:0] i_dg,
  input  wire [3:0] gsel,
  output wire [16*17-1:0] gsum,
  output wire [16*13-1:0] gbin,
  output wire busy
);
  ot_hdc_v41x_sel_hist #(.W(2), .CB(13)) u (.clk(clk), .rst_n(rst_n), .clr(clr), .i_v(i_v), .i_en(i_en),
    .i_dg(i_dg), .gsel(gsel), .gsum(gsum), .gbin(gbin), .busy(busy));
endmodule
module hfd_qsel_pack_k (
  input  wire clk, rst_n, i_v, i_fl,
  input  wire [15:0] i_sel,
  input  wire [16*37-1:0] i_p,
  output wire o_v,
  output wire [15:0] o_lv,
  output wire [16*37-1:0] o_line,
  output wire o_bv, o_fl
);
  ot_hdc_v41x_sel_pack #(.W(16), .PW(37)) u (.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_fl(i_fl), .i_sel(i_sel),
    .i_p(i_p), .o_v(o_v), .o_lv(o_lv), .o_line(o_line), .o_bv(o_bv), .o_fl(o_fl));
endmodule
`default_nettype wire
