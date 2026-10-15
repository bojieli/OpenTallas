`timescale 1ns/1ps
// Actual256-entry external host landing FIFO matching endpoint FCR256.
// Two real256x256 SRAMs; no initialized/software on-chip memory substitute.
// Single requested read, one registered SRAM edge, one output capture edge.
module ot_hbm_host_landing256(input wire clk,rst_n,
 input wire in_v,input wire[544:0]in_data,
 output reg out_v,output reg[511:0]out_data,input wire out_ready,
 output wire pop,output reg fault);
 reg[7:0]wp,rp;reg[8:0]count;reg pending;
 wire read_en=!out_v&&!pending&&(count!=0);
 wire consume=out_v&&out_ready;
 wire[511:0]mem_data;
`ifdef OT_HOST_LANDING_MUT_ADDR
 wire[7:0]read_addr=rp^8'd1;
`else
 wire[7:0]read_addr=rp;
`endif
 assign pop=consume;
 genvar b;generate for(b=0;b<2;b=b+1)begin:g_bank
 ot_sram_1r1w_256x256_m2_r2c2 u_mem(.clk(clk),.r_ce_in(read_en),.r_addr_in(read_addr),.rd_out(mem_data[b*256+:256]),
 .w_ce_in(in_v&&(count!=256)),.w_addr_in(wp),.wd_in(in_data[b*256+:256]),.w_mask_in({256{1'b1}}),
 .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end endgenerate
 always @(posedge clk)if(pending)out_data<=mem_data;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin wp<=0;rp<=0;count<=0;pending<=0;out_v<=0;fault<=0;end
 else begin
  pending<=read_en;
  if(in_v)begin
   if(count==256)fault<=1;else wp<=wp+1'b1;
   if(in_data[544:512]!==33'd0)fault<=1;
  end
  if(pending)out_v<=1;
  if(consume)begin out_v<=0;rp<=rp+1'b1;end
  case({in_v&&(count!=256),consume})
  2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;
  endcase
 end end
endmodule
