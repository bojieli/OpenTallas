`timescale 1ns/1ps
// REGISTERED_BOUNDARY quarter chain (additive; ot_hbm_native_quarter_chain is
// unchanged). Stations are ot_hbm_native_frame_station_rb: register-to-register
// boundaries, held valid / pulsed ready between stations (pure wire). The SM
// taps and the parent ACK are level-ready partners, so each gets the one-flop
// duplicate mask that a held-valid sender needs at a level-ready receiver.
// Station 0 holds its receipt for the parent (release_held=1); inner receipts
// are readyless pulses into the reserved upstream seat (release_held=0).
// Actual publication-parent quarter caller chain: fanouts3/3/3/2, two SMs
// per column, next-column branch2 except terminal. ZERO provider SRAM here.
// Actual caller root/cold POR feeds every station. Forwarded inverter roots
// are exported; measured receiver routing/SSF closure remain OPEN.
// Warm admission belongs to the publication parent; owed traffic drains here.
// NO2_CHAIN=1 (hardcore-1010 FALLBACK, default off): every NO3 column station is
// replaced by TWO NO2 stations in series (branch0 = one SM, branch1 = next
// station; the terminal NO2 keeps its two SMs): 7 identical NO2 stations per
// quarter, so the die replicates ONE hardened element (the CLOSED NO2 view).
// Same inter-station protocol as next_column (held valid / pulsed ready,
// readyless protected receipt into the upstream reserved ACK seat); same
// SM taps, owners, frames and receipts. Cost: +1 station hop (forward and
// receipt) per replaced column. fclk_o[c] is the first station of column c.
module ot_hbm_native_quarter_chain_rb #(parameter integer ENABLE=0,NO2_CHAIN=0)(
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
 localparam integer NS=NO2_CHAIN?7:4;
 wire [NS-1:0] iv,ir,empty,stop,failed,fck;
 wire [NS*2063-1:0] data;wire [NS*192-1:0] owner;wire [NS*73-1:0] frame;
 wire [NS-1:0] rv,rr;wire [NS*192-1:0] ro;wire [NS*73-1:0] rf;
 for(genvar c=0;c<4;c=c+1)begin:col_fclk assign fclk_o[c]=fck[NO2_CHAIN?2*c:c];end
 assign fault=|failed;assign drained=(&empty)&&!fault;
 assign warm_drained=ENABLE&&warm_req&&drained;assign paused=|stop;
 assign iv[0]=tap_v&&!fault;assign tap_r=ir[0]&&!fault;
 assign data[0+:2063]=tap_data;assign owner[0+:192]=tap_owner;assign frame[0+:73]=tap_frame;
 reg tj;reg [7:0] smj;
 always @(posedge clk_sm or negedge por_n)
  if(!por_n)begin tj<=0;smj<=0;end
  else begin tj<=tap_ACK_v&&tap_ACK_r;smj<=sm_v&sm_r;end
 assign tap_ACK_v=rv[0]&&!fault&&!tj;assign rr[0]=tap_ACK_r&&!fault&&!tj;
 assign tap_ACK_owner=ro[0+:192];assign tap_ACK_frame=rf[0+:73];
 for(genvar s=0;s<NS;s=s+1)begin:stage
  localparam integer F=(s==NS-1||NO2_CHAIN)?2:3;
  localparam integer NSM=(s==NS-1||!NO2_CHAIN)?2:1;
  localparam integer SM0=NO2_CHAIN?s:2*s;
  localparam [0:0] HELD=(s==0);
  wire [F-1:0] ov,ready,ack;wire [F*2063-1:0] od;
  wire [F*192-1:0] oo,ao;wire [F*73-1:0] ofr,af;
  ot_hbm_native_frame_station_rb #(.ENABLE(ENABLE),.NO(F)) u_station(
   .clk_sm(clk_sm),.por_n(por_n),.release_held(HELD),.in_v(iv[s]&&!fault),.in_r(ir[s]),
   .in_data(data[s*2063+:2063]),.in_owner(owner[s*192+:192]),.in_frame(frame[s*73+:73]),
   .out_v(ov),.out_r(ready),.out_data(od),.out_owner(oo),.out_frame(ofr),
   .ACK_v(ack),.ACK_owner(ao),.ACK_frame(af),
   .release_v(rv[s]),.release_r(rr[s]),.release_owner(ro[s*192+:192]),.release_frame(rf[s*73+:73]),
   .fclk_o(fck[s]),.drained(empty[s]),.paused(stop[s]),.fault(failed[s]));
  for(genvar t=0;t<NSM;t=t+1)begin:sm
   localparam integer I=SM0+t;
   assign sm_v[I]=ov[t]&&!fault&&!smj[I];assign ready[t]=sm_r[I]&&!fault&&!smj[I];
   assign sm_data[I*2063+:2063]=od[t*2063+:2063];
   assign sm_owner[I*192+:192]=oo[t*192+:192];assign sm_frame[I*73+:73]=ofr[t*73+:73];
   assign ack[t]=sm_ACK_v[I];assign ao[t*192+:192]=sm_ACK_owner[I*192+:192];
   assign af[t*73+:73]=sm_ACK_frame[I*73+:73];
  end
  if(s<NS-1)begin:next_column
   assign iv[s+1]=ov[NSM]&&!fault;assign ready[NSM]=ir[s+1]&&!fault;
   assign data[(s+1)*2063+:2063]=od[NSM*2063+:2063];
   assign owner[(s+1)*192+:192]=oo[NSM*192+:192];assign frame[(s+1)*73+:73]=ofr[NSM*73+:73];
   // Native ACK is readyless. Each protected downstream receipt supplies
   // one pulse to its upstream reserved ACK seat, with literal full frame.
   assign ack[NSM]=rv[s+1];assign rr[s+1]=!fault;
   assign ao[NSM*192+:192]=ro[(s+1)*192+:192];assign af[NSM*73+:73]=rf[(s+1)*73+:73];
  end
 end
endmodule
