`timescale 1ns/1ps
`default_nettype none
// Structural packing successor: same34 real1024x256 memories and one-edge
// old-data read. Eachlane has16code banks and one144-bit metadata bank.
// External packed265b/group ABI is unchanged. No behavioural payload storage.
module ot_hbm_attn_staging_grouped #(parameter integer MUT=0)(
 input wire clk,input wire[1:0]wr_en,input wire[8:0]wr_addr,
 input wire[8479:0]wr_data,input wire[8:0]rd_addr,
 output wire[8479:0]rd_data
);
 genvar l,g;
 for(l=0;l<2;l=l+1)begin:g_lane
  wire[143:0]meta_in,meta_out;wire[255:0]meta_q;
  for(g=0;g<16;g=g+1)begin:g_group
   wire[255:0]q;
   assign meta_in[g*9+:9]=wr_data[l*4240+g*265+256+:9];
   assign rd_data[l*4240+g*265+:256]=q;
   assign rd_data[l*4240+g*265+256+:9]=meta_out[g*9+:9];
   ot_sram_1r1w_1024x256_m2_r2c2 u_codes(
    .clk(clk),.r_ce_in(1'b1),.r_addr_in({1'b0,rd_addr}),.rd_out(q),
    .w_ce_in(wr_en[l]),.w_addr_in({1'b0,wr_addr}),
    .wd_in(wr_data[l*4240+g*265+:256]),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end
  assign meta_out=MUT==1?{meta_q[142:0],meta_q[143]}:meta_q[143:0];
  ot_sram_1r1w_1024x256_m2_r2c2 u_metadata(
   .clk(clk),.r_ce_in(1'b1),.r_addr_in({1'b0,rd_addr}),.rd_out(meta_q),
   .w_ce_in(wr_en[l]),.w_addr_in({1'b0,wr_addr}),
   .wd_in({112'b0,meta_in}),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end
endmodule
`default_nettype wire
