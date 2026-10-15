`timescale 1ns/1ps
`default_nettype none
// Typed compiler-mode ingress. Both input faces are physically captured; no
// producer output mux is inserted behind its face. Mode is an immutable slot
// instruction, not demand arbitration. Input sampledC ->outputafterC+1;
// downstream qslots samplesC+2. Faults never change the selected timeline.
module ot_hgi_coll_vm_idx_ingress #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire mode_idx,
 input wire [3:0] expected_v,
 input wire [3:0] vm_v,idx_v,
 input wire [2179:0] vm_d,idx_d,
 output reg [3:0] out_v,
 output reg [2179:0] out_d,
 output reg fault
);
 reg mode_q;reg [3:0] expected_q,vm_vq,idx_vq;
 reg [2179:0] vm_dq,idx_dq;
 always @(posedge clk)begin
  vm_dq<=vm_d;idx_dq<=idx_d;
  out_d<=(mode_q ^ (MUT==1))?idx_dq:vm_dq;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin mode_q<=0;expected_q<=0;vm_vq<=0;idx_vq<=0;out_v<=0;fault<=0;end
  else begin
   mode_q<=mode_idx;expected_q<=expected_v;vm_vq<=vm_v;idx_vq<=idx_v;
   out_v<=mode_q?idx_vq:vm_vq;
   if(MUT!=2 && ((mode_q && (|vm_vq)) || (!mode_q && (|idx_vq)) ||
     ((mode_q?idx_vq:vm_vq)!=expected_q)))fault<=1;
  end
 end
endmodule
`default_nettype wire
