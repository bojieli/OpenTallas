`timescale 1ns/1ps
`default_nettype none
// Opt-in SAFE-QW-CB16 column station. Same data-edge and TDM hold calendar
// as ot_qfd_xcst(AW24,NW18,XOFF3); reset is landed through two face stages.
// <=12 data bits per kept control region bounds combined cap/hold select loads.
(* keep_hierarchy="yes" *)
module qfd_c_xstn_safe_region #(parameter W=12)(
 input wire ck,rst_l0,go,input wire[2:0]sidx,
 input wire[7:0]tag,input wire[W-1:0]lo,hi,output wire[W-1:0]held);
 (* keep=1 *)reg r2;
 (* keep=1 *)reg[2:0]sx;
 (* keep=1 *)reg[3:0]cnt;
 (* keep=1 *)reg run;
 reg[W-1:0]cap;
 (* keep=1 *)reg[W-1:0]hold;
 wire a=tag[3]&&tag[2:0]==sx;
 wire b=tag[7]&&tag[6:4]==sx;
 always@(posedge ck)begin
  r2<=rst_l0;sx<=sidx;
  if(a)cap<=lo;else if(b)cap<=hi;
  if(run&&cnt==0)hold<=a?lo:b?hi:cap;
 end
 // The landed local reset controls only five state bits in this region.
 always@(posedge ck or negedge r2)
  if(!r2)begin cnt<=0;run<=0;end
  else if(go)begin cnt<=1;run<=1;end
  else if(run)cnt<=(cnt==0)?7:cnt-1'b1;
 assign held=hold;
endmodule

module qfd_c_xstn_safe(
 input wire ck,rst_n,input wire[2:0]sidx,input wire[515:0]b_d,
 output wire[515:0]a_d,output wire[507:0]tap_d);
 (* keep=1 *)reg[515:0]b_q;
 (* keep=1 *)reg rst_l0;
 always@(posedge ck)begin b_q<=b_d;rst_l0<=rst_n;end
 wire[63:0]held;
 genvar j;
 generate for(j=0;j<6;j=j+1)begin:g
  localparam N=(64-12*j<12)?64-12*j:12;
  qfd_c_xstn_safe_region #(.W(N))u(ck,rst_l0,b_q[0],sidx,b_q[515:508],b_q[380+12*j+:N],b_q[444+12*j+:N],held[12*j+:N]);
 end endgenerate
 wire[127:0]xo;
 generate for(j=0;j<4;j=j+1)begin:x
  assign xo[j*32+:32]={held[j*16+:16],16'h0000};
 end endgenerate
 assign a_d=b_q;
 assign tap_d={xo,b_q[379:0]};
endmodule

module qfd_c_xstnw_safe(
 input wire ck,rst_n,input wire[2:0]sidx,input wire[515:0]b_d,
 output wire[515:0]a_d,output wire[507:0]tap_d);
 qfd_c_xstn_safe u(ck,rst_n,sidx,b_d,a_d,tap_d);
endmodule
`default_nettype wire
