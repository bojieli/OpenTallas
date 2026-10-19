`timescale 1ns/1ps
// HBM-SMB-KITS: proposed source-compatible Gray FIFO using actual 8x285
// dual-clock SRAM. Sized first in uarch_model.hbm_svg_landing_macro_model.
// Not instantiated by release masters until component+landing+physical proof.
// MUT1 drops next-head lookahead; MUT2 reads the next slot (negative controls).
`default_nettype none
// SPSC Gray-pointer FIFO. Two pointer synchronizer stages in each direction;
// empty/full compare synchronized Gray pointers directly. Consumers capture
// rd_data on rd_valid&&rd_ready; pointer release follows that same edge.
// Data is held until the synchronized read pointer permits slot reuse.
module ot_hbm_svc_async_fifo_sram285 #(parameter integer WIDTH=285,DEPTH=8,MUT=0)(
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
 initial if(WIDTH!=285||DEPTH!=8)$fatal(1,"sram285 requires production 8x285 shape");
 reg [PW-1:0] wr_bin,wr_gray,rd_bin,rd_gray;
 (* async_reg="true" *)reg [PW-1:0] rd_gray_w1,rd_gray_w2,wr_gray_r1,wr_gray_r2;
 reg wr_online,rd_online;
 (* async_reg="true" *)reg rd_online_w1,rd_online_w2,wr_online_r1,wr_online_r2;
 wire full=wr_gray=={~rd_gray_w2[PW-1:PW-2],rd_gray_w2[PW-3:0]};
 wire empty=rd_gray==wr_gray_r2;
 assign wr_ready=wr_reset&&rd_online_w2&&!full;
 assign rd_valid=rd_reset&&wr_online_r2&&!empty;
 // The currently visible head was read on the preceding read-clock edge.
 // On a pop, synchronous SRAM reads the next head at that same edge. On
 // empty->nonempty, two Gray synchronizer edges ensure at least one actual
 // post-write macro read before rd_valid permits consumption. No asynchronous
 // macro data output or multi-cycle constraint is assumed.
 wire [AW-1:0] lookahead=rd_bin[AW-1:0]+((rd_valid&&rd_ready)?1'b1:1'b0);
 wire [AW-1:0] macro_raddr=(MUT==1)?rd_bin[AW-1:0]:(MUT==2)?lookahead+1'b1:lookahead;
 ot_sram_1r1w2c_8x285_m1 u_payload(.wclk(wr_clk),.rclk(rd_clk),
  .r_ce_in(1'b1),.r_addr_in(macro_raddr),.rd_out(rd_data),
  .w_ce_in(wr_fire),.w_addr_in(wr_bin[AW-1:0]),.wd_in(wr_data),.w_mask_in({WIDTH{1'b1}}));
 wire wr_fire=wr_valid&&wr_ready,rd_fire=rd_valid&&rd_ready;
 wire [PW-1:0] wr_next=wr_bin+wr_fire,rd_next=rd_bin+rd_fire;
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
   rd_bin<=0;rd_gray<=0;wr_gray_r1<=0;wr_gray_r2<=0;
   rd_online<=0;wr_online_r1<=0;wr_online_r2<=0;rd_underflow<=0;
  end else begin
   rd_online<=1;wr_online_r1<=wr_online;wr_online_r2<=wr_online_r1;
   wr_gray_r1<=wr_gray;wr_gray_r2<=wr_gray_r1;
   if(rd_ready&&!rd_valid)rd_underflow<=1;
   if(rd_fire)begin rd_bin<=rd_next;rd_gray<=(rd_next>>1)^rd_next;end
  end
 end
endmodule

