`timescale 1ns/1ps
// DIE-HBM-92-OPEN/OWNRF lock-step: main ot_svgr_own (RF1+RF2+RF3) vs RF4 (registered skid pop), same inputs, every output compared.
module ls_top #(parameter integer MUTB=0)(
 input wire clk, input wire rst_n,
 input wire seam_res_v,input wire[96:0]seam_res_word,input wire seam_s_fault,
 input wire [7:0] bk_cr,input wire [3:0] k_rdy,input wire [3:0] k_wr_done,
 input wire [3:0] kr_v,input wire [67:0] kr_tag,input wire [15:0] kr_beat,input wire [1023:0] kr_data,
 output wire a_seam_h_fault,output wire [7:0] a_bk_in_v,output wire [2279:0] a_bk_in_data,output wire [3:0] a_k_v,output wire [119:0] a_k_addr,
 output wire [15:0] a_k_len,output wire [67:0] a_k_tag,output wire [3:0] a_kr_rdy,
 output wire mism, output wire [3:0] cov_tail
);
 wire b_seam_h_fault;wire [7:0] b_bk_in_v;wire [2279:0] b_bk_in_data;wire [3:0] b_k_v;wire [119:0] b_k_addr;wire [15:0] b_k_len;wire [67:0] b_k_tag;wire [3:0] b_kr_rdy;
 wire [3:0] a_k_we,b_k_we;wire [1023:0] a_k_wdata,b_k_wdata;wire [127:0] a_k_wstrb,b_k_wstrb;
 ot_svgr_own a(.id_stack(2'd0),.id_sm(3'd0),.stream_clk(clk),.stream_rst_n(rst_n),.hbm_clk(clk),.hbm_rst_n(rst_n),.hbm_pc_clk({4{clk}}),
  .seam_res_v(seam_res_v),.seam_res_word(seam_res_word),.seam_s_fault(seam_s_fault),.seam_h_fault(a_seam_h_fault),
  .bk_in_v(a_bk_in_v),.bk_in_data(a_bk_in_data),.bk_cr(bk_cr),.k_v(a_k_v),.k_rdy(k_rdy),.k_addr(a_k_addr),.k_len(a_k_len),.k_tag(a_k_tag),.k_we(a_k_we),
  .k_wdata(a_k_wdata),.k_wstrb(a_k_wstrb),.k_wr_done(k_wr_done),.kr_v(kr_v),.kr_rdy(a_kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 ot_svgr_own_rf4x #(.MUT(MUTB)) b(.id_stack(2'd0),.id_sm(3'd0),.stream_clk(clk),.stream_rst_n(rst_n),.hbm_clk(clk),.hbm_rst_n(rst_n),.hbm_pc_clk({4{clk}}),
  .seam_res_v(seam_res_v),.seam_res_word(seam_res_word),.seam_s_fault(seam_s_fault),.seam_h_fault(b_seam_h_fault),
  .bk_in_v(b_bk_in_v),.bk_in_data(b_bk_in_data),.bk_cr(bk_cr),.k_v(b_k_v),.k_rdy(k_rdy),.k_addr(b_k_addr),.k_len(b_k_len),.k_tag(b_k_tag),.k_we(b_k_we),
  .k_wdata(b_k_wdata),.k_wstrb(b_k_wstrb),.k_wr_done(k_wr_done),.kr_v(kr_v),.kr_rdy(b_kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 assign mism = (a_seam_h_fault!==b_seam_h_fault)||(a_bk_in_v!==b_bk_in_v)||(a_bk_in_data!==b_bk_in_data)||(a_k_v!==b_k_v)||(a_k_addr!==b_k_addr)
  ||(a_k_len!==b_k_len)||(a_k_tag!==b_k_tag)||(a_kr_rdy!==b_kr_rdy)||(a_k_we!==b_k_we)||(a_k_wdata!==b_k_wdata)||(a_k_wstrb!==b_k_wstrb);
 // coverage: RF4 owner grants its TAIL (pop pending and the next entry granted in the same cycle)
 genvar p; generate for(p=0;p<4;p=p+1)begin:cv
  assign cov_tail[p]=b.acc_q[p]&&b.response_accepted[p];
 end endgenerate
endmodule
