`timescale 1ns/1ps
`default_nettype none
// Fixed schedule delay, II=1. The macro read ends at a local full-cycle
// capture; no SRAM-Q -> output pin combinational path. D counts captures,
// exactly as reference q[0:D-1]. SRAM contents are never reset or assumed zero.
module ot_hgi_coll_fixed_delay_sram #(
 parameter integer W=140,D=83,MUT_SLOT=0,MUT_RESET=0
)(input wire clk,rst_n,input wire [W-1:0] din,output reg [W-1:0] dout);
 localparam integer SMALL=(D<=32 && W<=128),DEPTH=SMALL?32:128,AW=SMALL?5:7,MW=SMALL?128:256;
 reg [W-1:0] in_q;
 reg [AW-1:0] wp;
 reg [7:0] filled;
 wire [AW-1:0] ra=wp-AW'(D-3)+(MUT_SLOT!=0?AW'(1):AW'(0));
 wire [MW-1:0] rd;
 wire [MW-1:0] wd={{(MW-W){1'b0}},in_q};
 generate if(SMALL)begin:g_small
 ot_sram_1r1w_32x128_m1 u_mem(.clk(clk),.r_ce_in(1'b1),.r_addr_in(ra),.rd_out(rd),
  .w_ce_in(1'b1),.w_addr_in(wp),.wd_in(wd),.w_mask_in({MW{1'b1}}));
 end else begin:g_large
 ot_sram_1r1w_128x256_m1_r2c2 u_mem(.clk(clk),.r_ce_in(1'b1),.r_addr_in(ra),.rd_out(rd),
  .w_ce_in(1'b1),.w_addr_in(wp),.wd_in(wd),.w_mask_in({MW{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 always @(posedge clk)begin
  in_q<=din;
  dout <= ((filled>=D-1)||(MUT_RESET!=0)) ? rd[W-1:0] : {W{1'b0}};
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wp<=0;filled<=0;end
  else begin wp<=wp+1'b1;if(filled<D)filled<=filled+1'b1;end
 end
 initial begin if(D<4 || D>DEPTH || W>MW)$fatal(1,"illegal fixed-delay shape");end
endmodule
`default_nettype wire
