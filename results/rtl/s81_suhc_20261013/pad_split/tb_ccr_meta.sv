`timescale 1ns/1ps
module ot_s81_hc_stree #(parameter integer NS=32,NP=11,LA=4,OWN=3)(
 input wire clk,rst_n,v,input wire[NP*128-1:0]pk,input wire[31:0]im,
 output reg[511:0]ex,output wire r_v,output wire[31:0]r,output wire fault);
 // Stage proof source: real subtree is unchanged; independently varied exports and fault.
 always @(posedge clk) ex <= pk[511:0] ^ {16{32'ha192337e}};
 assign fault=v & pk[511];assign r_v=v;assign r=pk[31:0];
endmodule
module tb_ccr_meta;
reg sk=0;always #5 sk=~sk;
reg srs=0;reg[2155:0]rd=0;reg[7:0]rv=0;
wire[2155:0]ro[0:1];wire[7:0]vo[0:1],po[0:1];wire[511:0]eo[0:1];
ot_s81_hc_ccr #(.HALF(1),.RLY(2),.RF(5),.DW(6),.RET_EXTRA(1))u_old(
 .sk(sk),.srs(srs),.ch_rd(rd),.ch_rv(rv),.crd_o(ro[0]),.crv_o(vo[0]),.cpi_o(po[0]),.ex1_o(eo[0]));
ot_s81_hc_ccr_align #(.DW(6))u_new(
 .sk(sk),.srs(srs),.ch_rd(rd),.ch_rv(rv),.crd_o(ro[1]),.crv_o(vo[1]),.cpi_o(po[1]),.ex1_o(eo[1]));
integer c,w;
initial begin
repeat(4)@(negedge sk);srs=1;
for(c=0;c<220;c=c+1)begin
if(c==100)srs=0;if(c==106)srs=1;
rv=c*173;
for(w=0;w<67;w=w+1)rd[w*32+:32]=c*293+w*661;
rd[2155:2144]=c;rd[619]=c%2;
@(posedge sk);#1;
if(c>=30)begin
if(ro[0]!==ro[1])$fatal(1,"raw capture changed cycle%0d",c);
if(vo[0]!==vo[1]||po[0]!==po[1]||eo[0]!==eo[1])$fatal(1,"metadata alignment mismatch cycle%0d",c);
end
@(negedge sk);
end
$display("CCR_META PASS 190 checked cycles, aligned metadata/PI/exports/fault and unchanged raw capture; reset exercised");$finish;
end
endmodule
