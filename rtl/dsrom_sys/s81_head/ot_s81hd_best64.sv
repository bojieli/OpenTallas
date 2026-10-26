`timescale 1ns/1ps
`default_nettype none
// HSF0 BEST transport over the current head's 64-wire lane. The real rank
// merge reads header[15:0] and the complete identity-bearing record[96:16].
// Canonical HSF0 BEST has last=1 and zero reserved payload[551:97]. Check
// those fields before compressing; never silently accept another frame type.
// Two consecutive registered beats contain {beat_index,valid,payload62}.
// Rate <= one BEST per 2 cycles. With S relay registers: visibility N+1+S
// edges, using the existing beat-link convention. No backpressure/credits.
// New module only: integrating it into hd_ctl/hd_mesh belongs to the head
// plan event and must price the extra serialization edge in the static model.
module ot_s81hd_best64_tx #(parameter integer MUT_IDENTITY=0)(
 input wire ck,rn,v,input wire [552:0] frame,
 output wire [63:0] lane,output wire fault
);
 wire canonical=frame[552] && frame[3:0]==4'd1 && !(|frame[551:97]);
 reg format_fault;
 always @(posedge ck or negedge rn)
  if(!rn) format_fault<=1'b0;
  else if(v&&!canonical) format_fault<=1'b1;
 wire [96:0] body=frame[96:0] ^ (MUT_IDENTITY ? (97'd1<<96) : 97'd0);
 wire tx_fault;
 ot_s81hd_beat_tx #(.W(97),.N(2),.P(62)) u_tx(
  .ck(ck),.rn(rn),.v(v&&canonical),.d(body),.o(lane),.fault(tx_fault));
 assign fault=format_fault|tx_fault;
endmodule
module ot_s81hd_best64_rx(
 input wire ck,rn,input wire [63:0] lane,
 output wire v,output wire [552:0] frame,output wire fault
);
 wire [96:0] body;wire word_v,beat_fault;
 ot_s81hd_beat_rx #(.W(97),.N(2),.P(62)) u_rx(
  .ck(ck),.rn(rn),.i(lane),.v(word_v),.d(body),.fault(beat_fault));
 wire best=body[3:0]==4'd1;
 reg type_fault;
 always @(posedge ck or negedge rn)
  if(!rn)type_fault<=1'b0;
  else if(word_v&&!best)type_fault<=1'b1;
 assign v=word_v&&best;
 assign frame={1'b1,455'd0,body};
 assign fault=beat_fault|type_fault;
endmodule
`default_nettype wire
