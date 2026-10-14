`default_nettype none
// Fixed logical depth, including head registers and prefetched records.
// A real macro's larger physical depth grants no additional caller credits.
// Internal SRAM clock pins are externally owned coherent-phase entries.
module ot_hbm_idx_landing_fifo_native #(
 parameter integer W=1098,AW=6,MUT=0,
 parameter integer MACRO=(AW==6)?0:1,
 parameter integer MB=(MACRO==0)?512:256,
 parameter integer NM=(W+MB-1)/MB
)(
 input wire clk,rst_n,
 input wire [NM-1:0] clk_mem,
 input wire we,input wire [W-1:0] wd,
 input wire re,
 output wire [W-1:0] rd,
 output wire ne,
 output reg [AW:0] cnt,
 output wire fault
);
 localparam integer DEPTH=1<<AW;
 wire ovf;
 reg bad;
 wire pop=re&&ne;
 wire space=(cnt<DEPTH)||pop;
 wire push=we && ((MUT==1)||space) && !fault;
 assign fault=bad||ovf;
 ot_hbm_idx_landing_store_native #(.W(W),.DEPTH(DEPTH),.MACRO(MACRO)) store(
  .clk(clk),.clk_mem(clk_mem),.rst_n(rst_n),.push(push),.wdata(wd),
  .pop(pop),.hv(ne),.head(rd),.ovf(ovf));
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin cnt<=0;bad<=0;end
  else begin
   cnt<=cnt+(push?1'b1:1'b0)-(pop?1'b1:1'b0);
   if(we&&!space && MUT!=1)bad<=1;
   if(pop&&cnt==0)bad<=1;
  end
endmodule
`default_nettype wire
