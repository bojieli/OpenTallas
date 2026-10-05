`timescale 1ps/1fs
// Additive finite C/A source selection. Model: hbm_pcwb_parent_model.py.
// One actual accepted command per channel/edge, pair parity aligned to CMD1.
// No synthetic PHY acceptance, credits, visibility or generated clock.
module ot_hbm_pcwb_ca_slots #(parameter integer ENABLE=0,NCH=16)(
 input wire service_clk,por_n,run_enable,
 input wire[2*NCH-1:0] row_req,
 input wire[6*NCH-1:0] row_op,
 input wire[10*NCH-1:0] row_bank,
 input wire[38*NCH-1:0] row_row,
 input wire[NCH-1:0] ca_ready,
 output wire[2*NCH-1:0] row_grant,
 output wire[NCH-1:0] ca_valid,
 output wire[NCH-1:0] ca_pc_lsb,
 output wire[3*NCH-1:0] ca_op,
 output wire[5*NCH-1:0] ca_bank,
 output wire[19*NCH-1:0] ca_row,
 output wire fault
);
 generate if(!ENABLE)begin:off
  assign row_grant=0;assign ca_valid=0;assign ca_pc_lsb=0;
  assign ca_op=0;assign ca_bank=0;assign ca_row=0;assign fault=0;
 end else begin:on
  reg parity,sticky;
  wire[NCH-1:0] conflict;
  // CMD1 internal phase toggles every service edge even when the caller is
  // not running. Do not freeze this parity independently of the controller.
  always @(posedge service_clk or negedge por_n)
   if(!por_n)begin parity<=0;sticky<=0;end
   else begin parity<=~parity;if(|conflict)sticky<=1;end
  assign fault=sticky||(|conflict);
  for(genvar c=0;c<NCH;c=c+1)begin:channel
   wire even_req=row_req[2*c],odd_req=row_req[2*c+1];
   assign conflict[c]=(even_req&&odd_req)||(even_req&&parity)||(odd_req&&!parity);
   wire selected=parity?odd_req:even_req;
   assign ca_valid[c]=selected&&run_enable&&!fault;
   assign ca_pc_lsb[c]=parity;
   assign ca_op[c*3+:3]=parity?row_op[(2*c+1)*3+:3]:row_op[(2*c)*3+:3];
   assign ca_bank[c*5+:5]=parity?row_bank[(2*c+1)*5+:5]:row_bank[(2*c)*5+:5];
   assign ca_row[c*19+:19]=parity?row_row[(2*c+1)*19+:19]:row_row[(2*c)*19+:19];
   assign row_grant[2*c]=ca_valid[c]&&ca_ready[c]&&!parity;
   assign row_grant[2*c+1]=ca_valid[c]&&ca_ready[c]&&parity;
  end
 end endgenerate
endmodule
