`timescale 1ns/1ps
`default_nettype none
// Native two-bank 1R1W exposure. Existing 22 macros are column-partitioned
// NM=3,3,3,2. Both physical banks can read while the selected bank writes.
// Caller must forbid a simultaneous read/write to the same bank/address.
// Inputs and macro outputs are registered locally; payload has no reset.
module vm_service_slice #(parameter integer NM=3)(
 input wire clk,rst_n,
 input wire w_v,w_bank,input wire [6:0] w_addr,
 input wire [NM*256-1:0] w_data,
 input wire [1:0] r_v,input wire [13:0] r_addr,
 output wire [1:0] rv,output wire [2*NM*256-1:0] rd);
 reg wv_q,wb_q;reg[6:0] wa_q;reg[NM*256-1:0] wd_q;
 reg[1:0] re_q,ret_q,rv_q;reg[13:0] ra_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin wv_q<=0;re_q<=0;ret_q<=0;rv_q<=0;end
  else begin wv_q<=w_v;re_q<=r_v;ret_q<=re_q;rv_q<=ret_q;end
 always @(posedge clk)begin wb_q<=w_bank;wa_q<=w_addr;wd_q<=w_data;ra_q<=r_addr;end
 for(genvar b=0;b<2;b=b+1)begin:banks
  wire [NM*256-1:0] q;reg[NM*256-1:0] data_q;
  for(genvar m=0;m<NM;m=m+1)begin:macros
   ot_sram_1r1w_128x256_m1_r2c2 u_sram(.clk(clk),
`ifdef MUT_SERVICE_SERIAL
    .r_ce_in(re_q[b]&&!wv_q),
`else
    .r_ce_in(re_q[b]),
`endif
    .r_addr_in(ra_q[b*7+:7]),.rd_out(q[m*256+:256]),
    .w_ce_in(wv_q&&(wb_q==1'(b))),.w_addr_in(wa_q),.wd_in(wd_q[m*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end
  always @(posedge clk)data_q<=q;
  assign rd[b*NM*256+:NM*256]=data_q;
 end
 assign rv=rv_q;
endmodule
`default_nettype wire
