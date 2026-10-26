`timescale 1ns/1ps
`default_nettype none
// Opt-in SAFE-QW-CB16 column station. Same data-edge and TDM hold calendar
// as ot_qfd_xcst(AW24,NW18,XOFF3); reset is landed through two face stages.
// <=12 data bits per kept control region bounds combined cap/hold select loads.
(* keep_hierarchy="yes" *)
module qfd_c_xstn_safe_region #(parameter W=12)(
 input wire ck,rst_l0,go_d,input wire[2:0]sidx,
 input wire[7:0]tag_d,input wire[W-1:0]lo,hi,output wire[W-1:0]held);
 // PLAN-QCv2 10-23: registered fanout tree. The tag word and the go bit are
 // registered here from the station input (same edge as the station's b_q),
 // one copy per region, so no single flop drives every region's selects
 // (a_d[515] drove 71 loads > 32 native). Cycle behaviour is unchanged.
 (* keep=1 *)reg[7:0]tag;
 (* keep=1 *)reg go;
 (* keep=1 *)reg r2;
 (* keep=1 *)reg[2:0]sx;
 (* keep=1 *)reg[3:0]cnt;
 (* keep=1 *)reg run;
 reg[W-1:0]cap;
 (* keep=1 *)reg[W-1:0]hold;
 wire a=tag[3]&&tag[2:0]==sx;
 wire b=tag[7]&&tag[6:4]==sx;
 always@(posedge ck)begin
  tag<=tag_d;go<=go_d;
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

// tap_p = {held[63:0], b_q[379:0]} (444 b). The former tap_d[507:380] packed each
// 16-b held word as {held,16'h0} (BF16 -> FP32 zero mantissa extension); the 64
// constant-zero halves are removed from the pin list (PLAN-QCv2 10-23, no tie-off
// on a partition/leaf pin). The consumer restores the format inside its
// partition, where the constants propagate in the flattened netlist (TOPDOWN L1).
// The port is renamed (tap_d -> tap_p) so a legacy 508-b binding fails to
// elaborate instead of silently shifting the held words.
module qfd_c_xstn_safe(
 input wire ck,rst_n,input wire[2:0]sidx,input wire[515:0]b_d,
 output wire[515:0]a_d,output wire[443:0]tap_p);
 (* keep=1 *)reg[515:0]b_q;
 (* keep=1 *)reg rst_l0;
 always@(posedge ck)begin b_q<=b_d;rst_l0<=rst_n;end
 wire[63:0]held;
 genvar j;
 generate for(j=0;j<6;j=j+1)begin:g
  localparam N=(64-12*j<12)?64-12*j:12;
  qfd_c_xstn_safe_region #(.W(N))u(ck,rst_l0,b_d[0],sidx,b_d[515:508],b_q[380+12*j+:N],b_q[444+12*j+:N],held[12*j+:N]);
 end endgenerate
 assign a_d=b_q;
 assign tap_p={held,b_q[379:0]};
endmodule

module qfd_c_xstnw_safe(
 input wire ck,rst_n,input wire[2:0]sidx,input wire[515:0]b_d,
 output wire[515:0]a_d,output wire[443:0]tap_p);
 qfd_c_xstn_safe u(ck,rst_n,sidx,b_d,a_d,tap_p);
endmodule
`default_nettype wire
