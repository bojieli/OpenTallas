`timescale 1ns/1ps
// Native status collector for six independently produced halfband L7 words.
// The compiler pads the status links to the same source-event edge before these
// pins. Inputs are cw0[2048] valid and cw0[2049] fault, not recreated schedule bits.
// Pure checking: faults never stall, gate, reschedule, or replace arithmetic.
module qfd_b2_word_status (
 input wire ck,rst_n,
 input wire [5:0] word_v,word_fault,
 output reg fault
);
 (* keep *) reg rs_q;
 (* keep *) reg [5:0] vq,fq;
 always @(posedge ck or negedge rst_n)if(!rst_n)rs_q<=0;else rs_q<=1;
 always @(posedge ck)begin vq<=word_v;fq<=word_fault;end
 always @(posedge ck or negedge rs_q)
  if(!rs_q)fault<=0;
  else fault<=fault | (|fq) | (|(vq ^ {6{vq[0]}}));
endmodule
