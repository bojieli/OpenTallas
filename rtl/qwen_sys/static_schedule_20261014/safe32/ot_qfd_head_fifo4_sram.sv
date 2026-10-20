`timescale 1ns/1ps
// Source-sized SRAM replacement for the head's four-word instruction FIFO.
// This is a new component; original head sources/defaults are unchanged.
// next_* are the original controller's next-state functions, not credits.
// read_addr_2next = fqrd_nx + next_hq_fill; each macro samples the registered
// lookahead at E and its result is consumed by the original hq fill at E+1.
// A same-address write/read forwards the actual word written at E. No data
// reset or SRAM initialization is required; the controller owns FIFO validity.
module ot_qfd_head_fifo4_sram #(parameter integer MUT=0) (
 input wire clk,
 input wire ck_pm0, ck_pm1,
 input wire [3:0] rst_leaf_n, // four identical two-stage landed parent leaves
 input wire write_next, read_run_next,
 input wire [1:0] write_addr_next, read_addr_2next,
 input wire [1023:0] write_data,
 output wire [1023:0] read_data
);
 // The unindexed last-write shadow is <=2kb, independent of FIFO depth.
 reg [1023:0] shadow;
 always @(posedge clk) shadow <= write_data;
 genvar b,s;
 generate for (b=0;b<8;b=b+1) begin:g_bank
  (* keep="true",dont_touch="true" *) reg wr_ce,rd_ce;
  (* keep="true",dont_touch="true" *) reg [1:0] wr_a,rd_a;
  wire rsl=rst_leaf_n[b/2];
  always @(posedge clk or negedge rsl)
   if(!rsl)begin wr_ce<=0;rd_ce<=0;end
   else begin wr_ce<=write_next && !(MUT==4 && b==0);rd_ce<=read_run_next;end
  always @(posedge clk)begin
   wr_a <= write_addr_next ^ ((MUT==3)?2'd1:2'd0);
   rd_a <= read_addr_2next - ((MUT==1)?2'd1:2'd0);
  end
  wire [127:0] q;
  ot_sram_1r1w_32x128_m1 u_mem (
   .clk((b<4)?ck_pm0:ck_pm1),.r_ce_in(rd_ce),.r_addr_in({3'd0,rd_a}),.rd_out(q),
   .w_ce_in(wr_ce),.w_addr_in({3'd0,wr_a}),.wd_in(write_data[128*b+:128]),
   .w_mask_in(128'hffffffffffffffffffffffffffffffff));
  // Eight kept match flags/bank,16 data muxes each. A single flag would
  // create a new128-load control. Address/CE copies are distinct per bank.
  for(s=0;s<8;s=s+1)begin:g_slice
   (* keep="true",dont_touch="true" *) reg forward_q;
   always @(posedge clk or negedge rsl)
    if(!rsl)forward_q<=0;
    else forward_q <= (MUT!=2) && wr_ce && rd_ce && wr_a==rd_a;
   assign read_data[128*b+16*s+:16] = forward_q ? shadow[128*b+16*s+:16] : q[16*s+:16];
  end
 end endgenerate
endmodule
