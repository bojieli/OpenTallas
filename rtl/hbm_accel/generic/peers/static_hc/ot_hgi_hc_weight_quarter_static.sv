`timescale 1ns/1ps
`default_nettype none
// One reusable HC quarter: two actual weight slots, local raw captures and
// selected output register. Parent straps bank/quarter IDs before reset release.
// ap sample n -> macro commit n+1; read macro n -> raw n+1 -> selected n+2.
// Downstream MAC capture n+3 is the unchanged TML3 read contract.
module ot_hgi_hc_weight_quarter_static #(
 parameter integer MUT_SLOT=0
)(
 input wire clk,rst_n,
 input wire [277:0] weight_ap,
 input wire [2:0] expected_bank_id,
 input wire [1:0] expected_quarter_id,
 input wire read_v,read_slot,
 input wire [6:0] read_row,
 output reg write_done,read_valid,fault,
 output reg [255:0] weight_data
);
 reg [277:0] ap_q;
 reg [2:0] bank_q;
 reg [1:0] quarter_q;
 reg ap_valid,slot_q,slot_qq,rv_q,rv_qq;
 wire [511:0] raw;
 reg [511:0] raw_capture;
 always @(posedge clk)begin
  ap_q<=weight_ap;bank_q<=expected_bank_id;quarter_q<=expected_quarter_id;
  slot_q<=read_slot;slot_qq<=slot_q;
  raw_capture<=raw;
  weight_data<=(slot_qq^(MUT_SLOT!=0))?raw_capture[256+:256]:raw_capture[0+:256];
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin ap_valid<=0;write_done<=0;rv_q<=0;rv_qq<=0;read_valid<=0;fault<=0;end
  else begin
   ap_valid<=weight_ap[277];
   write_done<=ap_valid&&(ap_q[264+:2]==quarter_q);
   rv_q<=read_v;rv_qq<=rv_q;read_valid<=rv_qq;
   if(ap_valid&&ap_q[273+:3]!=bank_q)fault<=1;
   if(ap_valid&&ap_q[264+:2]==quarter_q&&read_v&&ap_q[276]==read_slot&&ap_q[266+:7]==read_row)fault<=1;
  end
 end
 for(genvar s=0;s<2;s=s+1)begin:slot
  wire [255:0] mask;
  for(genvar w=0;w<8;w=w+1)begin:word
   assign mask[w*32+:32]={32{ap_q[w]}};
  end
  ot_sram_1r1w_128x256_m1_r2c2 u_weight(
   .clk(clk),.r_ce_in(read_v&&read_slot==1'(s)),.r_addr_in(read_row),.rd_out(raw[s*256+:256]),
   .w_ce_in(ap_valid&&ap_q[276]==1'(s)&&ap_q[273+:3]==bank_q&&ap_q[264+:2]==quarter_q),
   .w_addr_in(ap_q[266+:7]),.wd_in(ap_q[8+:256]),.w_mask_in(mask),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end
endmodule
`default_nettype wire
