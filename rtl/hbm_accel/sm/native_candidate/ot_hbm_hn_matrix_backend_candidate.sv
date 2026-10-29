// Explicit candidate only. No production caller selects this module.
// Source bodies: sm_native_kit.SOURCE_COMMIT and its guarded reset header.
// New backend ABI; it is NOT an adapter for ot_hbm_accel_smh_attn.
// model: tools.uarch_model.hbm_hn_matrix_backend_candidate_model().
module ot_hbm_hn_matrix_backend_candidate (
 input wire clk, rst_n,
 input wire [3271:0] row_left, row_right,
 input wire [4137:0] beat_left, beat_right,
 input wire [831:0] xs_config,
 output wire [1599:0] gather
);
 wire [26175:0] ri,ro;
 wire [33103:0] bi,bo;
 wire [3199:0] go;
 genvar c,p;
 generate for(c=0;c<8;c=c+1) begin:g_c
  for(p=0;p<2;p=p+1) begin:g_p
   localparam integer T=2*c+p;
   if(c==3) begin:g_left
    assign ri[1636*T+:1636]=row_left[1636*p+:1636];
    assign bi[2069*T+:2069]=beat_left[2069*p+:2069];
   end else if(c<3) begin:g_west
    assign ri[1636*T+:1636]=ro[1636*(T+2)+:1636];
    assign bi[2069*T+:2069]=bo[2069*(T+2)+:2069];
   end else if(c==4) begin:g_right
    assign ri[1636*T+:1636]=row_right[1636*p+:1636];
    assign bi[2069*T+:2069]=beat_right[2069*p+:2069];
   end else begin:g_east
    assign ri[1636*T+:1636]=ro[1636*(T-2)+:1636];
    assign bi[2069*T+:2069]=bo[2069*(T-2)+:2069];
   end
   wire [99:0] gi;
   if(p==0) begin:g_seed
    assign gi=100'b0; // Exact mathematical gather seed, as original SM column.
   end else begin:g_chain
    assign gi=go[200*(T-1)+:100];
   end
   // Both roots alias the SAME 833ps core clock. Equal-edge bin/reset fanout.
   // All26 XS bits perhalf are genuine inputs; boot provider remains required.
   hnx_rp3lp3x_halves u_pair(
    .rst_n(rst_n),.ck_n(clk),.ck_s(clk),
    .xs_a1(xs_config[52*T+:9]),.xs_g1(xs_config[52*T+9+:5]),
    .xs_a2(xs_config[52*T+14+:7]),.xs_g2(xs_config[52*T+21+:5]),
    .xss_a1(xs_config[52*T+26+:9]),.xss_g1(xs_config[52*T+35+:5]),
    .xss_a2(xs_config[52*T+40+:7]),.xss_g2(xs_config[52*T+47+:5]),
    .rin_n(ri[1636*T+:818]),.rin_s(ri[1636*T+818+:818]),
    .bin(bi[2069*T+:2069]),.gin(gi),
    .rout_n(ro[1636*T+:818]),.rout_s(ro[1636*T+818+:818]),
    .bout(bo[2069*T+:2069]),.gout(go[200*T+:200]));
  end
  assign gather[200*c+:200]=go[200*(2*c+1)+:200];
 end endgenerate
endmodule
