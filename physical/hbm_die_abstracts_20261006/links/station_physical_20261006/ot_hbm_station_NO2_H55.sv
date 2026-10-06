`timescale 1ns/1ps
// Selected physical variant; ONE parameterized station implementation.
module ot_hbm_station_NO2_H55 #(parameter integer ENABLE=0,NO=2)(
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
 initial if(ENABLE&&NO!=2)$fatal(1,"fixed actual NO2 ABI, no truncation");
 ot_hbm_native_frame_station #(.ENABLE(ENABLE),.NO(NO)) u_source(
  .clk_sm(clk_sm),
  .por_n(por_n),
  .in_v(in_v),
  .in_r(in_r),
  .in_data(in_data),
  .in_owner(in_owner),
  .in_frame(in_frame),
  .out_v(out_v),
  .out_r(out_r),
  .out_data(out_data),
  .out_owner(out_owner),
  .out_frame(out_frame),
  .ACK_v(ACK_v),
  .ACK_owner(ACK_owner),
  .ACK_frame(ACK_frame),
  .release_v(release_v),
  .release_r(release_r),
  .release_owner(release_owner),
  .release_frame(release_frame),
  .fclk_o(fclk_o),
  .drained(drained),
  .paused(paused),
  .fault(fault)
 );
endmodule
