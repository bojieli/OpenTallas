`default_nettype none
// SPSC Gray-pointer FIFO with its storage in a dual-clock 1R1W SRAM macro (L2H-IDXSCORE/SVG 2026-10-19, SAFE-DESIGN
// checklist item 5: runtime-indexed storage > ~2 kb is an SRAM, never a flop array).  Same ports and the same write
// side as ot_hbm_svc_async_fifo (wr_ready / wr_overflow bit-identical: slots are released on the read-side consume
// edge, as there); only Gray pointers, online flags and a 2-entry read-side output buffer are flops.
//   * write: the macro's w_* pins are driven from the wr_clk family only (w_ce = wr_fire, w_addr = wr_bin).
//   * read : r_addr_in = the fetch pointer (next slot to copy into the output buffer) from rd_clk flops (+1 when this
//            edge copies), so the macro reads mem[fetch] every rd edge; rd_out is captured into the buffer at the next
//            edge only when that slot is published by the synchronised write Gray pointer (wr_gray_r2 != fetch Gray,
//            evaluated from registers).  The published slot was written >= 1 rd edge before the macro read it (the
//            Gray pointer passes two rd flops after the write edge), so no read overlaps its own slot's write.
//   * rd_valid / rd_data come from buffer flops (no macro output reaches the consumer combinationally).
// LATENCY: +1 rd_clk edge from publish to rd_valid vs the flop FIFO (the capture edge); full rate (one word per rd edge)
// with the 2-entry buffer.  The FIFO is an elastic boundary (HBM response / descriptor crossing), so the static on-die
// schedule only sees the landing-complete edge (priced in the kit README: landing -> resident +1 stream edge,
// descriptor -> issue +1 hbm edge).
module ot_hbm_svc_async_fifo_sram #(parameter integer WIDTH=32,DEPTH=8)(
 input wire wr_clk,wr_rst_n,wr_valid,output wire wr_ready,
 input wire [WIDTH-1:0] wr_data,output reg wr_overflow,
 input wire rd_clk,rd_rst_n,output wire rd_valid,input wire rd_ready,
 output wire [WIDTH-1:0] rd_data,output reg rd_underflow
);
 localparam integer AW=$clog2(DEPTH),PW=AW+1;
 initial if(DEPTH<4||(DEPTH&(DEPTH-1))!=0)$error("FIFO depth must be power-of-two >=4");
 wire both_reset=wr_rst_n&&rd_rst_n;wire wr_reset,rd_reset;
 ot_reset_sync u_wr_reset(.clk(wr_clk),.async_rst_n(both_reset),.sync_rst_n(wr_reset));
 ot_reset_sync u_rd_reset(.clk(rd_clk),.async_rst_n(both_reset),.sync_rst_n(rd_reset));
 reg [PW-1:0] wr_bin,wr_gray,rd_bin,rd_gray,f_bin,f_gray;
 (* async_reg="true" *)reg [PW-1:0] rd_gray_w1,rd_gray_w2,wr_gray_r1,wr_gray_r2;
 reg wr_online,rd_online;
 (* async_reg="true" *)reg rd_online_w1,rd_online_w2,wr_online_r1,wr_online_r2;
 wire full=wr_gray=={~rd_gray_w2[PW-1:PW-2],rd_gray_w2[PW-3:0]};
 assign wr_ready=wr_reset&&rd_online_w2&&!full;
 wire wr_fire=wr_valid&&wr_ready;
 wire [PW-1:0] wr_next=wr_bin+wr_fire;
 // ---- read side: 2-entry output buffer (b0 = head)
 reg [1:0] bcnt;reg [WIDTH-1:0] b0,b1;
 wire head_v=bcnt!=0;
 assign rd_valid=rd_reset&&wr_online_r2&&head_v;
 assign rd_data=b0;
 wire rd_fire=rd_valid&&rd_ready;
`ifdef OT_SVG_FIFO_MUT_PUBLISH
 wire published=f_gray!=wr_gray;                   // mutant: unsynchronised write pointer (captures before publish)
`else
 wire published=f_gray!=wr_gray_r2;            // slot f_bin holds a written word (registers only)
`endif
 wire cap=rd_reset&&published&&(bcnt!=2'd2||rd_fire);
 wire [PW-1:0] f_next=f_bin+cap,rd_next=rd_bin+rd_fire;
 wire [WIDTH-1:0] mem_q;
 always @(posedge wr_clk or negedge wr_reset)begin
  if(!wr_reset)begin
   wr_bin<=0;wr_gray<=0;rd_gray_w1<=0;rd_gray_w2<=0;
   wr_online<=0;rd_online_w1<=0;rd_online_w2<=0;wr_overflow<=0;
  end else begin
   wr_online<=1;rd_online_w1<=rd_online;rd_online_w2<=rd_online_w1;
   rd_gray_w1<=rd_gray;rd_gray_w2<=rd_gray_w1;
   if(wr_valid&&!wr_ready)wr_overflow<=1;
   if(wr_fire)begin wr_bin<=wr_next;wr_gray<=(wr_next>>1)^wr_next;end
  end
 end
 always @(posedge rd_clk or negedge rd_reset)begin
  if(!rd_reset)begin
   rd_bin<=0;rd_gray<=0;f_bin<=0;f_gray<=0;bcnt<=0;wr_gray_r1<=0;wr_gray_r2<=0;
   rd_online<=0;wr_online_r1<=0;wr_online_r2<=0;rd_underflow<=0;
  end else begin
   rd_online<=1;wr_online_r1<=wr_online;wr_online_r2<=wr_online_r1;
   wr_gray_r1<=wr_gray;wr_gray_r2<=wr_gray_r1;
   if(rd_ready&&!rd_valid)rd_underflow<=1;
   if(rd_fire)begin rd_bin<=rd_next;rd_gray<=(rd_next>>1)^rd_next;end
   if(cap)begin f_bin<=f_next;f_gray<=(f_next>>1)^f_next;end
   bcnt<=bcnt+{1'b0,cap}-{1'b0,rd_fire};
  end
 end
 // buffer data (unreset): shift on consume, fill the first free entry on capture
 always @(posedge rd_clk)begin
  case({rd_fire,cap})
   2'b01:if(bcnt==0)b0<=mem_q;else b1<=mem_q;
   2'b10:b0<=b1;
   2'b11:if(bcnt==1)b0<=mem_q;else begin b0<=b1;b1<=mem_q;end
   default:;
  endcase
 end
`ifdef OT_SVG_FIFO_MUT_RADDR
 wire [AW-1:0] r_addr=f_bin[AW-1:0];                // mutant: macro reads the current, not the next fetch slot
`else
 wire [AW-1:0] r_addr=f_next[AW-1:0];
`endif
 generate if(WIDTH==285&&DEPTH==8)begin:g_m8x285
  ot_sram_1r1w2c_8x285_m1 u_mem(.wclk(wr_clk),.rclk(rd_clk),.r_ce_in(1'b1),.r_addr_in(r_addr),.rd_out(mem_q),
   .w_ce_in(wr_fire),.w_addr_in(wr_bin[AW-1:0]),.wd_in(wr_data),.w_mask_in({WIDTH{1'b1}}));
 end else if(WIDTH==97&&DEPTH==4)begin:g_m4x97
  ot_sram_1r1w2c_4x97_m1 u_mem(.wclk(wr_clk),.rclk(rd_clk),.r_ce_in(1'b1),.r_addr_in(r_addr),.rd_out(mem_q),
   .w_ce_in(wr_fire),.w_addr_in(wr_bin[AW-1:0]),.wd_in(wr_data),.w_mask_in({WIDTH{1'b1}}));
 end else begin:g_none
  initial $error("ot_hbm_svc_async_fifo_sram: no SRAM macro for WIDTH %0d DEPTH %0d", WIDTH, DEPTH);
  assign mem_q='0;
 end endgenerate
endmodule
`default_nettype wire
