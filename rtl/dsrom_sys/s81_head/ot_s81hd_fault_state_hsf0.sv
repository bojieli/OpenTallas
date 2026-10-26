`timescale 1ns/1ps
// Actual HSF0 sticky fault/state mechanism. LP fault is a LIVE input and owns
// bit10, exactly as the original controller. The other16 event producers stay
// explicit at the component boundary; this does not fabricate those producers.
module ot_s81hd_fault_state_hsf0 #(parameter integer MUT_LEP_DROP=0)(
 input wire ck,rst_vector_n,rst_output_n,
 input wire lep_fault_i,input wire[15:0] other_events_i,
 output wire[16:0] fault_vector,output wire ctl_fault
);
 reg lepf_q;
 reg[16:0] fv;
 reg ctlf_q;
 always@(posedge ck) lepf_q<=lep_fault_i;
 wire[16:0] fset={other_events_i[15:10],
                 (MUT_LEP_DROP ? 1'b0:lepf_q),other_events_i[9:0]};
 always@(posedge ck or negedge rst_vector_n)
  if(!rst_vector_n) fv<=17'd0; else fv<=fv|fset;
 always@(posedge ck or negedge rst_output_n)
  if(!rst_output_n) ctlf_q<=1'b0; else ctlf_q<=|fv;
 assign fault_vector=fv;
 assign ctl_fault=ctlf_q;
endmodule
