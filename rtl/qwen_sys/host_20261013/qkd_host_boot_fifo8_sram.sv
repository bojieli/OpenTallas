`timescale 1ns/1ps
// Logical depth-8 host boot FIFO payload store. Synchronous read address is the
// NEXT head selected before the clock (pop ? rp+1 : rp). The macro read-before-
// write collision is bypassed explicitly, including the first enqueue to empty.
// Capacity, enqueue/pop decisions, credits and externally visible edges belong
// to the original controller and remain unchanged. Three real 32x128 SRAMs;
// physical depth32, logical depth8. MUT1 drops RAW bypass; MUT2 reads wrong head.
`ifndef OT_HOST_ORDER_S2_DEFAULT
`define OT_HOST_ORDER_S2_DEFAULT 0
`endif
module qkd_host_boot_fifo8_sram #(parameter integer W=290, MUT=0, CACHE=`OT_HOST_ORDER_S2_DEFAULT)(
 input wire ck, input wire wr, input wire[2:0]wp, input wire[W-1:0]wd,
 input wire[2:0]rp,next_rp, output wire[W-1:0]head);
 wire[383:0]padded={{(384-W){1'b0}},wd};
 wire[383:0]mem_q;
 wire[2:0]base_ra=CACHE?next_rp+3'd2:next_rp;
 wire[2:0]ra=(MUT==2)?base_ra+3'd1:base_ra;
 reg raw; reg[W-1:0]raw_data;
 always @(posedge ck)begin
  raw <= wr && (wp==ra);
  if(wr && (wp==ra))raw_data<=wd;
 end
 for(genvar b=0;b<3;b++)begin:g_bank
  ot_sram_1r1w_32x128_m1_p192 u_mem(.clk(ck),.r_ce_in(1'b1),.r_addr_in({2'b0,ra}),
   .rd_out(mem_q[b*128+:128]),.w_ce_in(wr),.w_addr_in({2'b0,wp}),
   .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
 end
 wire[W-1:0]third=(raw && MUT!=1)?raw_data:mem_q[W-1:0];
 generate if(CACHE)begin:g_cache
  // Two forward words isolate macro clk->q from external output edges.
  // The third word was requested for the old current head on the prior edge.
  reg[W-1:0]first,second;
  wire advance=next_rp!=rp;
  always @(posedge ck)begin
   if(wr&&wp==next_rp)first<=wd;
   else if(advance)first<=(MUT==3)?third:second;
   if(wr&&wp==next_rp+3'd1)second<=wd;
   else if(advance)second<=third;
  end
  assign head=first;
 end else begin:g_direct
  assign head=third;
 end endgenerate
endmodule
