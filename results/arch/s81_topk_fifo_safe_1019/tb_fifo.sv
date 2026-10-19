`timescale 1ns/1ps
`ifndef MUT
`define MUT 0
`endif
module one #(parameter W=592, AW=3)(input clk,input rst_n,input integer cyc,output integer errors,output integer checks);
 localparam D=1<<AW;
 reg [AW-1:0] rp=0,wp=0; integer cnt=0; reg [W-1:0] refq[0:D-1];
 wire push=(cyc%64< D) ? cnt<D : (cyc%64< D+4) ? 0 : (cyc%64< D+20) ? 0 : (cnt<D || pop) && ((cyc%7)!=0);
 wire pop=cnt!=0 && ((cyc%64>=D+4 && cyc%64<D+20) || (cyc%64>=D+20 && (cyc%5)!=0));
 wire [AW-1:0] nrp=rp+AW'(pop);
 wire [W-1:0] data= W'({32'(cyc),32'(~cyc),32'(cyc*71+3),32'(cyc*97+5),32'(cyc*113+9),32'(cyc*67+1),32'(cyc*43+7),32'(cyc*19+11),32'(cyc*17+13),32'(cyc*79+17),32'(cyc*41+19),32'(cyc*83+23),32'(cyc*53+29),32'(cyc*31+31),32'(cyc*23+37),32'(cyc*11+41),32'(cyc*59+43),32'(cyc*61+47),32'(cyc*73+53)});
 wire [W-1:0] head;
 ot_s81ph_queue_store #(.W(W),.AW(AW),.MUT(`MUT)) q(.clk(clk),.rst_n(rst_n),.push(push&&rst_n),.wa(wp),.data(data),.next_head(nrp),.head(head));
 initial begin errors=0;checks=0;end
 always @(posedge clk) begin
  if(!rst_n) begin rp<=0;wp<=0;cnt<=0;end
  else begin
   if(push) begin refq[wp]<=data;wp<=wp+1'b1;end
   if(pop)rp<=rp+1'b1;
   cnt<=cnt+int'(push)-int'(pop);
   #1;
   if(cnt>0) begin checks=checks+1;if(head!==refq[rp])begin errors=errors+1;if(errors<4)$display("BAD W%0d cyc%0d cnt%0d rp%0d head%h want%h",W,cyc,cnt,rp,head,refq[rp]);end end
  end
 end
endmodule
module tb_fifo;
 reg clk=0,rst_n=0;integer cyc=0;wire integer e0,e1,c0,c1;
 always #5 clk=~clk;
 one #(.W(592),.AW(3)) a(clk,rst_n,cyc,e0,c0);
 one #(.W(593),.AW(2)) b(clk,rst_n,cyc,e1,c1);
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  for(integer k=0;k<24000;k=k+1)begin @(negedge clk);cyc=k;if(k%997==995)rst_n=0;if(k%997==996)rst_n=1;end
  @(negedge clk);$display("FIFO_CHECK errors=%0d checks=%0d",e0+e1,c0+c1);
  if(e0+e1!=0)$fatal(1,"FIFO FAIL");$display("FIFO PASS");$finish;
 end
endmodule
