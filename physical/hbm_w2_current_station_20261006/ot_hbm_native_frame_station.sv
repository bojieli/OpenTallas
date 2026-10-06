`timescale 1ns/1ps
// Source-ready single-element binding around the ONE native station primitive.
// Full73 frame remains distinct from owner192. ACK means destination visibility.
// Opt-in held retirement waits for a real protected full-frame reverse seat.
module ot_hbm_native_frame_station #(parameter integer REGISTERED_CURRENT=0,ENABLE=0,NO=3)(
 input wire clk_sm,por_n,
 input wire in_v,output wire in_r,input wire [2062:0] in_data,
 input wire [191:0] in_owner,input wire [72:0] in_frame,
 output wire [NO-1:0] out_v,input wire [NO-1:0] out_r,
 output wire [NO*2063-1:0] out_data,output wire [NO*192-1:0] out_owner,
 output wire [NO*73-1:0] out_frame,
 input wire [NO-1:0] ACK_v,input wire [NO*192-1:0] ACK_owner,
 input wire [NO*73-1:0] ACK_frame,
 output wire release_v,input wire release_r,
 output wire [191:0] release_owner,output wire [72:0] release_frame,
 output wire fclk_o,drained,paused,fault
);
 generate if(!ENABLE)begin:disabled
  assign in_r=0;assign out_v=0;assign out_data=0;assign out_owner=0;assign out_frame=0;
  assign release_v=0;assign release_owner=0;assign release_frame=0;
  assign fclk_o=0;assign drained=1;assign paused=0;assign fault=0;
 end else begin:held
  initial if(NO!=2&&NO!=3)$fatal(1,"actual quarter station NO2 terminal/NO3 2SM+next only");
  wire [NO*2136-1:0] payload;
  wire [NO-1:0] valid,ready,bad;
  wire native_fault,native_empty,native_pause,pulse,native_r;
  wire receipt_room,receipt_v,receipt_empty,receipt_fault;
  wire [264:0] receipt;
  wire guard_normal,guard_fault,guard_repair;wire [63:0] unused;
  wire frame_bad=|bad;
  assign fault=frame_bad||guard_fault||native_fault||receipt_fault;
  assign in_r=native_r&&!fault;
  assign out_v=valid&{NO{!fault}};assign ready=out_r&{NO{!fault}};
  assign release_v=receipt_v&&!fault;
  assign release_frame=receipt[264:192];assign release_owner=receipt[191:0];
  assign drained=native_empty&&receipt_empty&&guard_normal&&!fault;
  assign paused=native_pause||guard_repair||(!receipt_empty&&!receipt_v&&!receipt_fault);
  ot_hbm_w2_protected_bank_current_pipeline #(.REGISTERED_CURRENT(REGISTERED_CURRENT),.WORDS(1)) u_frame_guard(
   .clk(clk_sm),.por_n(por_n),.load(1'b0),.load_encoded(1'b0),.fatal(frame_bad),
   .d(64'b0),.encoded_d(72'b0),.q(unused),.encoded_q(),
   .normal(guard_normal),.fault(guard_fault),.repairing(guard_repair));
  ot_hbm_w2_protected_cut_current_pipeline #(.REGISTERED_CURRENT(REGISTERED_CURRENT),.W(265)) u_receipt(
   .clk(clk_sm),.por_n(por_n),.in_v(pulse&&!fault),.in_r(receipt_room),
   .in_d({payload[2063+:73],out_owner[0+:192]}),
   .out_v(receipt_v),.out_r(release_r&&!fault),.out_d(receipt),
   .empty(receipt_empty),.fault(receipt_fault));
  ot_hbm_native_station #(.REGISTERED_CURRENT(REGISTERED_CURRENT),.MODE(1),.ENABLE(1),.W(2136),.IW(2136),.NI(1),.NO(NO),.RELEASE_BACKPRESSURE(1)) u_native(
   .fclk_i(clk_sm),.rst_n({4{por_n}}),.i_v(1'b0),.i_d(2136'b0),.fclk_o(fclk_o),.o_v(),.o_d(),
   .quiesce(!receipt_room||!guard_normal||fault),
   .in_v(in_v&&!fault),.in_r(native_r),.in_data({in_frame,in_data}),.in_owner(in_owner),
   .out_v(valid),.out_r(ready),.out_data(payload),.out_owner(out_owner),
   .ACK_v(ACK_v&{NO{!(frame_bad||guard_fault||receipt_fault)}}),.ACK_owner(ACK_owner),
   .source_release_r(receipt_room&&guard_normal&&!fault),.source_release(pulse),
   .drained(native_empty),.paused(native_pause),.fault(native_fault));
  for(genvar t=0;t<NO;t=t+1)begin:branch
   assign out_data[t*2063+:2063]=payload[t*2136+:2063];
   assign out_frame[t*73+:73]=payload[t*2136+2063+:73];
   assign bad[t]=ACK_v[t]&&(ACK_frame[t*73+:73]!=payload[t*2136+2063+:73]);
  end
 end endgenerate
endmodule
