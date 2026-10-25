`timescale 1ns/1ps
module tb;
localparam integer N=3400;
reg ck=0,rn=0;always #0.5 ck=~ck;reg[275:0]vi=0,vo=0;wire[275:0]lo;wire[15:0]st;
reg[275:0]a[0:N-1],b[0:N-1];string cas="multi",fn;integer cyc=0,nreq=0,nret=0;reg olddone=0;
dsdv_idx_tx_i13 #(.D(128),.C(1024),.SRAM_MACRO(0),.MUT(0))dut(ck,rn,vi,vo,lo,st);
always @(posedge ck)begin #0.1;if(vo[0]&&vo[3:1]==0&&vo[28:21]==8'h5c&&vo[31:29]==2)$display("JOB_ACCEPT %0d",cyc);
if(dut.done&&!olddone)$display("JOB_DONE %0d",cyc);
olddone=dut.done;
if(lo[0])$display("LO %0d %h",cyc,lo);cyc=cyc+1;end
initial begin void'($value$plusargs("CASE=%s",cas));fn={cas,"_vi.hex"};$readmemh(fn,a);fn={cas,"_vo.hex"};$readmemh(fn,b);repeat(10)@(negedge ck);rn=1;for(integer i=0;i<N;i++)begin @(negedge ck);vi=a[i];vo=b[i];end @(negedge ck);$display("I13_RESULT case=%s st=%h fault=%0d",cas,st,st[0]);$finish;end
endmodule
