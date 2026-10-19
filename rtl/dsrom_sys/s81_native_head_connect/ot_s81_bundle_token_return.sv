`timescale 1ns/1ps
import ot_rom_coll_pkg::*;
// Minimum live component connection. Fixed issue slots are external; ready
// signals only detect a collision. This is not the physical die return link.
module ot_s81_bundle_token_return (
 input wire clk,rst_n,go,
 input wire [46:0] request_owner,
 input wire [63:0] request_sequence,
 input wire [16:0] row0,
 input wire [255:0] xa,xb,
 output wire [3:0] head_valid,
 output wire [127:0] head_bits,
 output wire [67:0] head_rows,
 output reg token_valid,
 output reg [31:0] token_id,token_bits,
 output reg [46:0] token_owner,
 output reg [63:0] token_sequence,
 output wire fault
);
 wire bundle_fault,unused_res_v;
 wire [16:0] unused_res_row;
 wire [31:0] unused_res_bits;
 ot_dsrom_head_bundle #(.INSTANCE("h"),.IOREG(1),.SAFE(1),.CUT(511),.SPLIT9(1)) u_field (
  .clk(clk),.rst_n(rst_n),.go(go),.row0(row0),.xa(xa),.xb(xb),
  .res_v(unused_res_v),.res_row(unused_res_row),.res_bits(unused_res_bits),.fault(bundle_fault),
  .head_v(head_valid),.head_d(head_bits),.head_row(head_rows));
 reg active,protocol_fault;
 reg [46:0] owner;
 reg [63:0] sequence_q;
 wire lg_ready,dn_valid,dn_last,arg_fault;
 wire [511:0] dn_data;
 wire [127:0] ids;
 wire last=(head_valid[3] && head_rows[51+:17]==row0+17'd127);
 for(genvar q=0;q<4;q=q+1) begin:g_ids
  assign ids[32*q+:32]={15'd0,head_rows[17*q+:17]};
 end
 wire [31:0] count;
 ot_rom_argmax_rows #(.LANES(4),.DEPTH(2),.FIRST(1),.SELF(0),.NEXT(1)) u_argmax (
  .clk(clk),.rst_n(rst_n),.lg_valid(|head_valid),.lg_ready(lg_ready),
  .lg_data(head_bits),.lg_mask(head_valid),.lg_base(32'd0),.lg_ids(ids),.lg_tag(8'd0),.lg_last(last),
  .up_valid(1'b0),.up_ready(),.up_data(512'd0),.up_last(1'b0),
  .dn_valid(dn_valid),.dn_ready(1'b1),.dn_data(dn_data),.dn_last(dn_last),.tokens_out(count),.fault(arg_fault));
 assign fault=bundle_fault|arg_fault|protocol_fault;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin active<=0;protocol_fault<=0;token_valid<=0;owner<=0;sequence_q<=0;
   token_id<=0;token_bits<=0;token_owner<=0;token_sequence<=0;end
  else begin
   token_valid<=0;
   if(go) begin
    if(active) protocol_fault<=1;
    else begin active<=1;owner<=request_owner;sequence_q<=request_sequence;end
   end
   if((|head_valid)&&(!active||!lg_ready)) protocol_fault<=1;
   if(dn_valid) begin
    if(!active||!dn_last||dn_data[H_KIND+:4]!=K_ARGMAX||!dn_data[H_ARG_OK]) protocol_fault<=1;
    else begin token_valid<=1;token_id<=dn_data[H_ARG_ID+:32];token_bits<=dn_data[H_ARG_VAL+:32];
     token_owner<=owner;token_sequence<=sequence_q;active<=0;end
   end
  end
 end
endmodule
