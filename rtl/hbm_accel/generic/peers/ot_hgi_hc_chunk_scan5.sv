`timescale 1ns/1ps
`default_nettype none
// Bounded two-packet scan leaf: pin capture, constant-width select, publication.
module ot_hgi_hc_chunk_scan2 #(parameter integer MUT=0)(
 input wire clk,rst_n,clr,input wire v0,v1,
 input wire[127:0]d0_lo,d0_hi,d1_lo,d1_hi,input wire[6:0]m0,m1,
 output reg out_v,output wire[127:0]out_lo,out_hi,output reg[6:0]out_meta,
 output reg fault
);
 wire[0:0]rn;ot_rst_relay #(.REGIONS(1))u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
 reg[1:0]vq;reg[255:0]a,b;reg[6:0]ma,mb;reg clear_q;reg[255:0]data;
 assign {out_hi,out_lo}=data;
 always @(posedge clk)begin a<={d0_hi,d0_lo};b<={d1_hi,d1_lo};ma<=m0;mb<=m1;end
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin vq<=0;clear_q<=1;end else begin vq<={v1,v0};clear_q<=clr;end
 end
 always @(posedge clk)begin
  data<=(a&{256{vq[0]}})|((MUT==1?a:b)&{256{vq[1]}});
  out_meta<=(ma&{7{vq[0]}})|(mb&{7{vq[1]}});
 end
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin out_v<=0;fault<=0;end
  else begin out_v<=(|vq)&&!clear_q;if(clear_q)fault<=0;else if(&vq)fault<=1;end
 end
endmodule
// Wires-only quarter tree. Four bounded scan2 leaves plus four CLOSED relay
// masters align the fifth packet path; no additional hard hierarchy is made.
module ot_hgi_hc_chunk_scan5 #(parameter integer CLOCKED=0,MUT=0)(
 input wire clk,rst_n,clr,input wire[7:0]clk_leaf,input wire[4:0]in_v,
 input wire[5*256-1:0]in_data,input wire[6:0]in_meta,
 output wire out_v,output wire[255:0]out_data,output wire[6:0]out_meta,
 output wire fault
);
 wire[7:0]ck=CLOCKED?clk_leaf:{8{clk}};
 wire[263:0]p[0:8];wire[3:0]f;
 for(genvar k=0;k<5;k++)assign p[k]={in_v[k],in_meta,in_data[k*256+:256]};
 wire[303:0]r[0:4];assign r[0]={40'd0,p[4]};
 for(genvar k=0;k<4;k++)begin:g_r
  hbfd_rly_304_WE u_r(.ck(ck[4+k]),.rs(rst_n),.i(r[k]),.o(r[k+1]));
 end
 for(genvar k=0;k<4;k++)begin:g_m
  wire[263:0]l=(k==0)?p[0]:(k==1)?p[2]:(k==2)?p[5]:p[7];
  wire[263:0]r_=(k==0)?p[1]:(k==1)?p[3]:(k==2)?p[6]:r[4][263:0];
  ot_hgi_hc_chunk_scan2 #(.MUT(MUT))u_m(.clk(ck[k]),.rst_n(rst_n),.clr(clr),
   .v0(l[263]),.v1(r_[263]),.d0_lo(l[127:0]),.d0_hi(l[255:128]),
   .d1_lo(r_[127:0]),.d1_hi(r_[255:128]),.m0(l[262:256]),.m1(r_[262:256]),
   .out_v(p[5+k][263]),.out_lo(p[5+k][127:0]),.out_hi(p[5+k][255:128]),
   .out_meta(p[5+k][262:256]),.fault(f[k]));
 end
 assign {out_v,out_meta,out_data}=p[8];assign fault=|f;
endmodule
`default_nettype wire
