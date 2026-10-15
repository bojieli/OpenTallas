`timescale 1ns/1ps
`default_nettype none
// Actual SC/E source buffer for one head. Eight native SRAMs receive an
// eight-sector VM response. Compiler chooses MAX_SC versus SUM_E residency;
// no internal operand is supplied by a software arithmetic model.
// Request a source word one edge before issuing its reduction command.
module ot_hbm_p_reduce_ingress_static (
 input wire clk,rst_n,
 input wire fill_slot,
 input wire [3:0] fill_burst,
 input wire [2055:0] vm_rr,
 input wire source_read,
 input wire [9:0] source_word,
 output reg source_valid,
 output wire [31:0] source_fp32,
 output reg fault
);
 wire [255:0] q[0:7];
 reg [2:0] bank_q,word_q;
 assign source_fp32=q[bank_q][32*word_q+:32];
 genvar b;
 generate for(b=0;b<8;b=b+1) begin:g_bank
  ot_sram_1r1w_128x256_m1_r2c2 u_source(
   .clk(clk),.r_ce_in(source_read&&source_word[5:3]==3'(b)),
   .r_addr_in({3'b0,source_word[9:6]}),.rd_out(q[b]),
   .w_ce_in(fill_slot),.w_addr_in({3'b0,fill_burst}),
   .wd_in(vm_rr[257*b+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 always @(posedge clk) begin
  if(!rst_n)begin source_valid<=0;bank_q<=0;word_q<=0;fault<=0;end
  else begin
   source_valid<=source_read;
   if(source_read)begin bank_q<=source_word[5:3];word_q<=source_word[2:0];end
   for(integer i=0;i<8;i=i+1)
    if(vm_rr[257*i+256]!=fill_slot)fault<=1;
   if((fill_slot&&fill_burst>=10)||(source_read&&source_word>=640))fault<=1;
  end
 end
endmodule
`default_nettype wire
