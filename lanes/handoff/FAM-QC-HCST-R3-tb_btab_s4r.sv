`timescale 1ns/1ps
module ot_sram_1r1w_128x256_m1_r2c2(input clk,r_ce_in,input [6:0]r_addr_in,output reg [255:0]rd_out,input w_ce_in,input [6:0]w_addr_in,input [255:0]wd_in,w_mask_in,input [1:0]rr_en,input [11:0]rr_addr,input [1:0]cr_en,input [15:0]cr_sel);
 reg [255:0] m[0:127]; always @(posedge clk) begin if(w_ce_in) m[w_addr_in]<=wd_in; if(r_ce_in) rd_out<=m[r_addr_in]; end endmodule
module tb; reg ck=0; always #5 ck=~ck;
 reg re=0; reg [8:0] w=0; reg we=0; reg [1:0] kind=0; reg [23:0] a=0; reg [1023:0] d=0;
 wire [127:0] l0,h0,l1,h1;
 qfd_dv_s5_btab_s4  A(.ck(ck),.bt_re(re),.bt_word(w),.bt_ql(l0),.bt_qh(h0),.tw_we(we),.tw_kind(kind),.tw_addr(a),.tw_lo(d[511:0]),.tw_hi(d[1023:512]));
 qfd_dv_s5_btab_s4r B(.ck(ck),.bt_re(re),.bt_word(w),.bt_ql(l1),.bt_qh(h1),.tw_we(we),.tw_kind(kind),.tw_addr(a),.tw_lo(d[511:0]),.tw_hi(d[1023:512]));
 reg [255:0] pq; integer i,err=0;
 always @(posedge ck) pq <= {h0,l0};
 always @(negedge ck) if (i>40) begin if ({h1,l1} !== pq) err=err+1; end
 initial begin
  for(i=0;i<600;i=i+1) begin @(negedge ck);
   we=(i<200); kind=2; a=i[8:0]; d={4{$random,$random,$random,$random,$random,$random,$random,$random}};
   re=(i>=200)&&($random&1); w=$random;
  end
  $display("RESULT mismatches=%0d", err); $finish; end
endmodule
