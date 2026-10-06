`timescale 1ns/1ps
// Actual publication-parent quarter caller chain: fanouts3/3/3/2, two SMs
// per column, next-column branch2 except terminal. ZERO provider SRAM here.
// Actual caller root/cold POR feeds every station. Forwarded inverter roots
// are exported; measured receiver routing/SSF closure remain OPEN.
// Warm admission belongs to the publication parent; owed traffic drains here.
module ot_hbm_native_quarter_chain #(parameter integer ENABLE=0)(
 input wire clk_sm,por_n,warm_req,
 input wire tap_v,output wire tap_r,
 input wire [2062:0] tap_data,input wire [191:0] tap_owner,input wire [72:0] tap_frame,
 output wire tap_ACK_v,input wire tap_ACK_r,
 output wire [191:0] tap_ACK_owner,output wire [72:0] tap_ACK_frame,
 output wire [7:0] sm_v,input wire [7:0] sm_r,
 output wire [8*2063-1:0] sm_data,output wire [8*192-1:0] sm_owner,
 output wire [8*73-1:0] sm_frame,
 input wire [7:0] sm_ACK_v,input wire [8*192-1:0] sm_ACK_owner,
 input wire [8*73-1:0] sm_ACK_frame,
 output wire [3:0] fclk_o,output wire drained,warm_drained,paused,fault
);
 wire [3:0] iv,ir,empty,stop,failed;
 wire [4*2063-1:0] data;wire [4*192-1:0] owner;wire [4*73-1:0] frame;
 wire [3:0] rv,rr;wire [4*192-1:0] ro;wire [4*73-1:0] rf;
 assign fault=|failed;assign drained=(&empty)&&!fault;
 assign warm_drained=ENABLE&&warm_req&&drained;assign paused=|stop;
 assign iv[0]=tap_v&&!fault;assign tap_r=ir[0]&&!fault;
 assign data[0+:2063]=tap_data;assign owner[0+:192]=tap_owner;assign frame[0+:73]=tap_frame;
 assign tap_ACK_v=rv[0]&&!fault;assign rr[0]=tap_ACK_r&&!fault;
 assign tap_ACK_owner=ro[0+:192];assign tap_ACK_frame=rf[0+:73];
 for(genvar s=0;s<4;s=s+1)begin:stage
  localparam integer F=s==3?2:3;
  wire [F-1:0] ov,ready,ack;wire [F*2063-1:0] od;
  wire [F*192-1:0] oo,ao;wire [F*73-1:0] ofr,af;
  ot_hbm_native_frame_station #(.ENABLE(ENABLE),.NO(F)) u_station(
   .clk_sm(clk_sm),.por_n(por_n),.in_v(iv[s]&&!fault),.in_r(ir[s]),
   .in_data(data[s*2063+:2063]),.in_owner(owner[s*192+:192]),.in_frame(frame[s*73+:73]),
   .out_v(ov),.out_r(ready),.out_data(od),.out_owner(oo),.out_frame(ofr),
   .ACK_v(ack),.ACK_owner(ao),.ACK_frame(af),
   .release_v(rv[s]),.release_r(rr[s]),.release_owner(ro[s*192+:192]),.release_frame(rf[s*73+:73]),
   .fclk_o(fclk_o[s]),.drained(empty[s]),.paused(stop[s]),.fault(failed[s]));
  for(genvar t=0;t<2;t=t+1)begin:sm
   localparam integer I=s*2+t;
   assign sm_v[I]=ov[t]&&!fault;assign ready[t]=sm_r[I]&&!fault;
   assign sm_data[I*2063+:2063]=od[t*2063+:2063];
   assign sm_owner[I*192+:192]=oo[t*192+:192];assign sm_frame[I*73+:73]=ofr[t*73+:73];
   assign ack[t]=sm_ACK_v[I]&&!fault;assign ao[t*192+:192]=sm_ACK_owner[I*192+:192];
   assign af[t*73+:73]=sm_ACK_frame[I*73+:73];
  end
  if(s<3)begin:next_column
   assign iv[s+1]=ov[2]&&!fault;assign ready[2]=ir[s+1]&&!fault;
   assign data[(s+1)*2063+:2063]=od[2*2063+:2063];
   assign owner[(s+1)*192+:192]=oo[2*192+:192];assign frame[(s+1)*73+:73]=ofr[2*73+:73];
   // Native ACK is readyless. Each protected downstream receipt supplies
   // one pulse to its upstream reserved ACK seat, with literal full frame.
   assign ack[2]=rv[s+1]&&!fault;assign rr[s+1]=!fault;
   assign ao[2*192+:192]=ro[(s+1)*192+:192];assign af[2*73+:73]=rf[(s+1)*73+:73];
  end
 end
endmodule
