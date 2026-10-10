`timescale 1ns/1ps
// Two RESERVED native ot_s81ph_vm_mem request slots. Never invent extra ports
// on the hardened VM master: its wrapper must allocate these slots explicitly.
// The VM orders issue edge then port index, so write0 precedes read1. Its o_v1
// is the actual read return, including bank arbitration and all physical hops.
module ot_s81_vm_adapter(
 input wire clk,rst_n,input wire we,input wire[13:0] wa,input wire[511:0] wd,
 input wire re,input wire[13:0] ra,
 output wire[1:0] i_v,output wire[1:0] i_we,output wire[27:0] i_row,
 output wire[31:0] i_mask,output wire[1023:0] i_d,
 input wire[1:0] o_v,input wire[1023:0] o_d,input wire vm_fault,
 output wire rq_v,output wire[511:0] rq,output reg fault
);
 assign i_v={re,we};assign i_we=2'b01;assign i_row={ra,wa};
 assign i_mask={16'd0,16'hffff};assign i_d={512'd0,wd};
 assign rq_v=o_v[1];assign rq=o_d[1023:512];
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;else if(vm_fault||o_v[0])fault<=1;
endmodule
