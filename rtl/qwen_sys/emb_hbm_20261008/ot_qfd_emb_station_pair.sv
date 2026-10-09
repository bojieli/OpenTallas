`timescale 1ns/1ps
// Actual core-domain packet stations. Pipeline slots never create credits.
// STAGES=0 preserves the previous direct wiring; each enabled stage adds one
// core edge independently to command and return, preserving every packet bit.
module ot_qfd_emb_station_pair #(parameter integer STAGES=0)(
 input wire clk,rst_n,
 input wire [287:0] cmd_i,output wire [287:0] cmd_o,
 input wire [259:0] ret_i,output wire [259:0] ret_o
);
 generate if(STAGES==0) begin: direct
  assign cmd_o=cmd_i;
  assign ret_o=ret_i;
 end else begin: piped
  (* keep *) reg [287:0] cmd_q[0:STAGES-1];
  (* keep *) reg [259:0] ret_q[0:STAGES-1];
  integer n;
  always @(posedge clk or negedge rst_n)
   if(!rst_n) begin
    for(n=0;n<STAGES;n=n+1) begin cmd_q[n]<=288'b0;ret_q[n]<=260'b0;end
   end else begin
    cmd_q[0]<=cmd_i;ret_q[0]<=ret_i;
    for(n=1;n<STAGES;n=n+1) begin cmd_q[n]<=cmd_q[n-1];ret_q[n]<=ret_q[n-1];end
   end
  assign cmd_o=cmd_q[STAGES-1];
  assign ret_o=ret_q[STAGES-1];
 end endgenerate
endmodule
