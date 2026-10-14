`timescale 1ns/1ps
`default_nettype none
// One golden 32-chunk block. Two local ingress slots belong to its quarter.
// The parent filters epoch/quarter/range and grants reads; this leaf owns local
// data/valid state, duplicate checking, and registered eight-chunk scan outputs.
module ot_hgi_hc_chunk_store32 #(parameter integer MUT=0)(
 input wire clk,rst_n,clr,
 input wire [1:0] wr_v,input wire [9:0] wr_tag,input wire [63:0] wr_data,
 input wire scan_v,input wire [1:0] scan_group,
 output reg scan_o_v,output reg [255:0] scan_data,
 output reg full,output reg fault
);
 wire [0:0]rn;ot_rst_relay #(.REGIONS(1))u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
 reg clear_q,sv_q;reg[1:0]wv_q,group_q;reg[9:0]tag_q;reg[63:0]data_q;
 reg[31:0]valid;reg[31:0]store[0:31];
 always @(posedge clk)begin tag_q<=wr_tag;data_q<=wr_data;group_q<=scan_group;end
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin clear_q<=1;wv_q<=0;sv_q<=0;end
  else begin clear_q<=clr;wv_q<=wr_v;sv_q<=scan_v;end
 end
 // Constant destinations avoid a wide variable write shifter at synthesis.
 for(genvar n=0;n<32;n=n+1)begin:g_word
  wire a=wv_q[0]&&tag_q[4:0]==5'(n);
  wire b=wv_q[1]&&tag_q[9:5]==5'(n);
  always @(posedge clk)if(!clear_q)begin
   if(a)store[n]<=data_q[31:0]^((MUT==1)?32'd1:32'd0);
   else if(b)store[n]<=data_q[63:32]^((MUT==1)?32'd1:32'd0);
  end
  always @(posedge clk or negedge rn[0])begin
   if(!rn[0])valid[n]<=0;
   else if(clear_q)valid[n]<=0;
   else if(a||b)valid[n]<=1;
  end
 end
 wire duplicate=(wv_q[0]&&valid[tag_q[4:0]])||(wv_q[1]&&valid[tag_q[9:5]])||
                 ((&wv_q)&&tag_q[4:0]==tag_q[9:5]);
 wire[255:0]group_data[0:3];
 for(genvar g=0;g<4;g=g+1)begin:g_scan
  for(genvar k=0;k<8;k=k+1)assign group_data[g][k*32+:32]=store[g*8+k];
 end
 wire[255:0]selected=(group_data[0]&{256{group_q==0}})|(group_data[1]&{256{group_q==1}})|
                         (group_data[2]&{256{group_q==2}})|(group_data[3]&{256{group_q==3}});
 always @(posedge clk)if(sv_q&&!clear_q)scan_data<=selected;
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin scan_o_v<=0;full<=0;fault<=0;end
  else begin
   scan_o_v<=sv_q&&!clear_q;full<=(&valid)&&!clear_q;
   if(clear_q)fault<=0;
   else if(duplicate&&MUT!=2)fault<=1;
  end
 end
endmodule
`default_nettype wire
