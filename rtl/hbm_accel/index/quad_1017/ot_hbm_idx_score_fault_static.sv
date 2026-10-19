`timescale 1ns/1ps
`default_nettype none
// Internal diagnostic stage of the quarter scorer, clocked by its existing ctl
// clock/reset. Input score is already registered; data bits are intentionally
// unreset. Match native engine cnt_faults: only valid keys with arithmetic
// faults count. Unused/padded lanes and invalid beats must never raise faults.
// Protocol sources retain the original quarter sticky-fault semantics.
// MUT1 drops arithmetic errors; MUT2 ignores key-valid; MUT3 ignores beat-valid.
module ot_hbm_idx_score_fault_static #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire [17:0] score_status,
 input wire [3:0] protocol_fault,
 output reg fault
);
 wire valid_score=(MUT==3)?1'b1:score_status[0];
 wire [7:0] valid_key=(MUT==2)?8'hff:score_status[17:10];
 wire [7:0] arithmetic_fault=(MUT==1)?8'd0:score_status[9:2];
 wire bad_score=valid_score && |(valid_key & arithmetic_fault);
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=1'b0;
  else if((|protocol_fault)||bad_score)fault<=1'b1;
endmodule
`default_nettype wire
