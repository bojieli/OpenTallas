`timescale 1ns/1ps
// Independent performance banks; no fault mirrors or protection protocol.
// The spare payload may capture unused data whenever empty. Its valid bit is
// unchanged, and a full spare holds until promoted to the output.
(* keep_hierarchy = "yes" *)
module ot_hfd_mtp_skid_bank_cx #(parameter integer W=64,MUT_SPARE=0)(
 input wire clk,rst_n,in_v,output reg in_ready,input wire[W-1:0]in_d,
 output reg out_v,input wire out_ready,output reg[W-1:0]out_d
);
 reg s_v;reg[W-1:0]s_d;
 wire in_fire=in_v&&in_ready;
 always@(posedge clk or negedge rst_n)begin
  if(!rst_n)begin out_v<=0;s_v<=0;in_ready<=0;end
  else begin
   if(!out_v||out_ready)begin
    if(s_v)begin out_v<=1;s_v<=0;end else out_v<=in_fire;
   end else if(in_fire)s_v<=1;
   in_ready<=(!out_v||out_ready)||!(s_v||in_fire);
  end
 end
 always@(posedge clk)begin
  if(!out_v||out_ready)out_d<=s_v?s_d:in_d;
  if(!s_v||MUT_SPARE!=0)s_d<=in_d;
 end
endmodule

module ot_hfd_mtp_skid_banked_cx #(parameter integer W=4105,BANKED=0,MUT_SPARE=0)(
 input wire clk,rst_n,in_v,output wire in_ready,input wire[W-1:0]in_d,
 output wire out_v,input wire out_ready,output wire[W-1:0]out_d
);
 generate if(BANKED==0)begin:legacy
  ot_hfd_mtp_skid #(.W(W)) unchanged(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_ready(in_ready),
   .in_d(in_d),.out_v(out_v),.out_ready(out_ready),.out_d(out_d));
 end else begin:banked
  localparam integer NB=(W+63)/64;
  wire[NB-1:0]ready_,valid_;
  assign in_ready=ready_[0];assign out_v=valid_[0];
  for(genvar b=0;b<NB;b=b+1)begin:bank
   localparam integer BW=(b*64+64<=W)?64:W-b*64;
   (* keep_hierarchy = "yes" *) ot_hfd_mtp_skid_bank_cx #(.W(BW),.MUT_SPARE(MUT_SPARE)) local_slice(
    .clk(clk),.rst_n(rst_n),.in_v(in_v),.in_ready(ready_[b]),.in_d(in_d[b*64+:BW]),
    .out_v(valid_[b]),.out_ready(out_ready),.out_d(out_d[b*64+:BW]));
  end
 end endgenerate
endmodule
