`timescale 1ns/1ps
// Default-off bounded reset farm. Same 3-edge release as SYNC2/TREE1.
// Literal1 root captures are kept separately: one drives <=32 data pins,
// the other drives <=32 asynchronous clear pins. All assertions propagate async.
module ot_rst_relay_bounded32 #(parameter integer REGIONS=128,MUT=0)(
 input wire clk,rst_n_in,output wire [REGIONS-1:0] rst_n);
 localparam integer GROUPS=(REGIONS+31)/32;
 generate if(REGIONS<1 || REGIONS>256) begin: bad ot_rst_relay_bounded32_bad_REGIONS trap(); end endgenerate
 (* keep="true",dont_touch="true",async_reg="true" *) reg [GROUPS-1:0] data_root,reset_root;
 genvar g,r;
 generate for(g=0;g<GROUPS;g=g+1) begin: roots
  always @(posedge clk or negedge rst_n_in)
   if(!rst_n_in) begin data_root[g]<=1'b0;reset_root[g]<=1'b0;end
   else begin data_root[g]<=1'b1;reset_root[g]<=1'b1;end
 end
 for(r=0;r<REGIONS;r=r+1) begin: region
  (* keep="true",dont_touch="true",async_reg="true" *) reg second;
  (* keep="true",dont_touch="true" *) reg leaf;
  always @(posedge clk or negedge reset_root[r/32])
   if(!reset_root[r/32]) second<=1'b0;else second<=data_root[r/32];
  always @(posedge clk or negedge second)
   if(!second) leaf<=1'b0;else leaf<=second;
  assign rst_n[r]=(MUT==1)?second:((MUT==2)?1'b1:leaf);
 end endgenerate
endmodule
