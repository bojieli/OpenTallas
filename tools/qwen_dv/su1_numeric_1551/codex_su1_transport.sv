`timescale 1ns/1ps
// PRIVATE numerical vehicle, not a physical/POR replacement.
module codex_su1_transport #(parameter integer EXTRA=4,WCOMP=4,CDEPTH=2,RDEPTH=2,ODEPTH=3)(input wire clk,rst_n,input wire[759:0] ci,output wire[247:0] co);
wire[759:0] adapted, entered; wire[247:0] raw;
generate if(WCOMP>0)begin:g_wc
reg[255:0] p[0:WCOMP-1];integer k;always @(posedge clk)begin p[0]<=ci[255:0];for(k=1;k<WCOMP;k=k+1)p[k]<=p[k-1];end
assign adapted={ci[759:256],p[WCOMP-1]};end else assign adapted=ci;endgenerate
generate if(CDEPTH>0)begin:g_in
reg[759:0] p[0:CDEPTH-1];integer k;always @(posedge clk)begin p[0]<=adapted;for(k=1;k<CDEPTH;k=k+1)p[k]<=p[k-1];end
assign entered=p[CDEPTH-1];end else assign entered=adapted;endgenerate
codex_su1_numeric_core #(.EXTRA(EXTRA)) u(.clk(clk),.rst_n(rst_n),.c_i(entered),.c_o(raw));
localparam[247:0] REQMASK=248'h000000000000007ffffffffffffffffff00000000000000000000001ffffff;
for(genvar b=0;b<248;b=b+1)begin:g_out
localparam integer D=REQMASK[b]?RDEPTH:ODEPTH;
if(D>0)begin:g_d
reg[D-1:0] p;always @(posedge clk) p<=(p<<1)|raw[b];assign co[b]=p[D-1];end else assign co[b]=raw[b];end
endmodule
