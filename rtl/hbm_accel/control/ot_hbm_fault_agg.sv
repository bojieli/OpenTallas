`timescale 1ns/1ps
`default_nettype none
// Inputs are synchronous event pulses. Async regions must transport them
// losslessly with an event mailbox/FIFO; a two-flop pulse sampler is invalid.
module ot_hbm_fault_agg #(parameter integer N=16)(
 input wire clk,rst_n,
 input wire [N-1:0] ce_v,ue_v,
 input wire hbm_poison,link_ue,su_fault,clear_when_idle,idle,
 output reg fault,irq, output reg [31:0] cause,n_ce,n_ue
);
 integer i; reg [31:0] ce_n,ue_n,events;
 function automatic [31:0] satadd(input [31:0] a,b);
  reg [32:0] s;begin s={1'b0,a}+{1'b0,b};satadd=s[32]?32'hffffffff:s[31:0];end
 endfunction
 always @* begin
  ce_n=0;ue_n=0;events=0;
  for(i=0;i<N;i=i+1) begin
   ce_n=ce_n+ce_v[i];ue_n=ue_n+ue_v[i];
   if(ue_v[i]) events[i%29]=1'b1;
  end
  events[29]=hbm_poison;events[30]=link_ue;events[31]=su_fault;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin fault<=0;irq<=0;cause<=0;n_ce<=0;n_ue<=0;end
  else begin
   irq<=0;
   n_ce<=satadd(n_ce,ce_n);n_ue<=satadd(n_ue,ue_n);
   if(clear_when_idle && idle) begin fault<=0;cause<=0;end
   // Event wins over clear: simultaneous UE must never be erased.
   if(|events) begin fault<=1;cause<=((clear_when_idle && idle)?32'b0:cause)|events;irq<=!fault || (clear_when_idle && idle);end
  end
endmodule
`default_nettype wire
