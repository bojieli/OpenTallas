`timescale 1ns/1ps
// Logical depth-8 host boot FIFO payload store. Synchronous read address is the
// NEXT head selected before the clock (pop ? rp+1 : rp). The macro read-before-
// write collision is bypassed explicitly, including the first enqueue to empty.
// Capacity, enqueue/pop decisions, credits and externally visible edges belong
// to the original controller and remain unchanged. Three real 32x128 SRAMs;
// physical depth32, logical depth8. MUT1 drops RAW bypass; MUT2 reads wrong head.
module qkd_host_boot_fifo8_sram #(parameter integer W=290, MUT=0)(
 input wire ck, input wire wr, input wire[2:0]wp, input wire[W-1:0]wd,
 input wire[2:0]next_rp, output wire[W-1:0]head);
 wire[383:0]padded={{(384-W){1'b0}},wd};
 wire[383:0]mem_q;
 wire[2:0]ra=(MUT==2)?next_rp+3'd1:next_rp;
 reg raw; reg[W-1:0]raw_data;
 always @(posedge ck)begin
  raw <= wr && (wp==ra);
  if(wr && (wp==ra))raw_data<=wd;
 end
 for(genvar b=0;b<3;b++)begin:g_bank
  ot_sram_1r1w_32x128_m1 u_mem(.clk(ck),.r_ce_in(1'b1),.r_addr_in({2'b0,ra}),
   .rd_out(mem_q[b*128+:128]),.w_ce_in(wr),.w_addr_in({2'b0,wp}),
   .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
 end
 assign head=(raw && MUT!=1)?raw_data:mem_q[W-1:0];
endmodule
