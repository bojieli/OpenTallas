`timescale 1ns/1ps
// Actual quarter caller binding: three 2SM+next stages, then two SMs.
// Single shared station implementation, not four independently hardened masters.
// Source ABI is VM publication parent's tap_data2063/owner192/frame73.
// Destination ACK is a real visibility receipt, never inferred from tap_r.
// Source ACK is held v/r/full192/full73, matching that parent's tap_ACK ABI.
// clk_sm/por_n are the actual caller root/cold reset at every station. The
// four inverter outputs are exported; their receiver timing remains OPEN.
// warm_req does not cancel already accepted/provider-owned publications.
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
 wire [3:0] iv,ir,release_p,empty,stop,st_fault,receipt_v,receipt_r,receipt_empty,receipt_fault;
 wire [4*2136-1:0] id;
 wire [4*192-1:0] io;
 wire [4*265-1:0] receipt;
 wire guard_normal,guard_fault,guard_repair;
 wire frame_bad;
 wire [63:0] unused_guard;
 assign fault=guard_fault||frame_bad||(|st_fault)||(|receipt_fault);
 assign iv[0]=ENABLE&&tap_v&&!fault;
 assign tap_r=ENABLE&&ir[0]&&!fault;
 assign id[0+:2136]={tap_frame,tap_data};assign io[0+:192]=tap_owner;
 assign tap_ACK_v=ENABLE&&receipt_v[0]&&!fault;
 assign tap_ACK_frame=receipt[192+:73];assign tap_ACK_owner=receipt[0+:192];
 assign receipt_r[0]=tap_ACK_r&&!fault;
 assign drained=(&empty)&&(&receipt_empty)&&guard_normal&&!fault;
 assign warm_drained=ENABLE&&warm_req&&drained;
 assign paused=(|stop)||guard_repair;
 wire [7:0] bad_frame;
 assign frame_bad=ENABLE&&(|bad_frame);
 ot_hbm_w2_protected_bank #(.WORDS(1)) u_frame_guard(
  .clk(clk_sm),.por_n(por_n),.load(1'b0),.load_encoded(1'b0),.fatal(frame_bad),
  .d(64'b0),.encoded_d(72'b0),.q(unused_guard),.encoded_q(),
  .normal(guard_normal),.fault(guard_fault),.repairing(guard_repair));
 for(genvar s=0;s<4;s=s+1)begin:stage
  localparam integer F=s==3?2:3;
  wire [F-1:0] ov,ready,ack;
  wire [F*2136-1:0] od;wire [F*192-1:0] oo,ao;
  wire [265-1:0] full_receipt={od[2063+:73],oo[0+:192]};
  wire receipt_room;
  // Full73/192 source-release pulse is captured in a real protected seat.
  // There is no permission to drop a pulse while the parent holds ACK_ready0.
  ot_hbm_w2_protected_cut #(.W(265)) u_receipt(
   .clk(clk_sm),.por_n(por_n),.in_v(ENABLE&&release_p[s]&&!fault),.in_r(receipt_room),
   .in_d(full_receipt),.out_v(receipt_v[s]),.out_r(receipt_r[s]),
   .out_d(receipt[s*265+:265]),.empty(receipt_empty[s]),.fault(receipt_fault[s]));
  ot_hbm_native_station #(.MODE(1),.ENABLE(ENABLE),.W(2136),.IW(2136),.NI(1),.NO(F),.RELEASE_BACKPRESSURE(1)) u_station(
   .fclk_i(clk_sm),.rst_n({4{por_n}}),.i_v(1'b0),.i_d(2136'b0),
   .fclk_o(fclk_o[s]),.o_v(),.o_d(),.quiesce(!receipt_room||!guard_normal||fault),
   .in_v(iv[s]&&!fault),.in_r(ir[s]),.in_data(id[s*2136+:2136]),.in_owner(io[s*192+:192]),
   .out_v(ov),.out_r(ready),.out_data(od),.out_owner(oo),
   .ACK_v(ack),.ACK_owner(ao),.source_release_r(receipt_room&&guard_normal&&!fault),.source_release(release_p[s]),.drained(empty[s]),.paused(stop[s]),.fault(st_fault[s]));
  for(genvar t=0;t<2;t=t+1)begin:sm
   localparam integer I=s*2+t;
   assign sm_v[I]=ov[t]&&!fault;
   assign ready[t]=sm_r[I]&&!fault;
   assign sm_data[I*2063+:2063]=od[t*2136+:2063];
   assign sm_frame[I*73+:73]=od[t*2136+2063+:73];
   assign sm_owner[I*192+:192]=oo[t*192+:192];
   assign bad_frame[I]=sm_ACK_v[I]&&(sm_ACK_frame[I*73+:73]!=od[t*2136+2063+:73]);
   assign ack[t]=ENABLE&&sm_ACK_v[I]&&!fault;
   assign ao[t*192+:192]=sm_ACK_owner[I*192+:192];
  end
  if(s<3)begin:next_column
   assign iv[s+1]=ov[2]&&!fault;assign ready[2]=ir[s+1]&&!fault;
   assign id[(s+1)*2136+:2136]=od[2*2136+:2136];
   assign io[(s+1)*192+:192]=oo[2*192+:192];
   // Native ACK has no ready: one protected receipt, consumed once, supplies
   // the upstream reserved ACK seat. It is never a repeated held pulse.
   assign ack[2]=receipt_v[s+1]&&!fault;
   assign ao[2*192+:192]=receipt[(s+1)*265+:192];
   assign receipt_r[s+1]=!fault;
  end
 end
endmodule
