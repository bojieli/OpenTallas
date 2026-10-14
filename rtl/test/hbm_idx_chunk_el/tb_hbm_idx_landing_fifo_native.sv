`timescale 1ns/1ps
module native_fifo_case #(parameter W=1098,AW=6,CAP_ATTACK=0,MUT=0)(input wire clk,output reg done);
 localparam DEPTH=1<<AW;
 localparam MB=(AW==6)?512:256;
 localparam NM=(W+MB-1)/MB;
 reg rst_n=0,we=0,re=0;reg [W-1:0]wd;
 wire ne,fault;wire[W-1:0]rd;wire[AW:0]cnt;
 ot_hbm_idx_landing_fifo_native #(.W(W),.AW(AW),.MUT(MUT))dut(
  .clk(clk),.clk_mem({NM{clk}}),.rst_n(rst_n),.we(we),.wd(wd),.re(re),.rd(rd),.ne(ne),.cnt(cnt),.fault(fault));
 function automatic [W-1:0]word(input integer n);
  reg[W-1:0]v;integer i;
  begin for(i=0;i<W;i=i+1)v[i]=((n*17+i*13)>>(i%17))&1;word=v;end
 endfunction
 integer sent=0,received=0,cycles=0,resets=0,full_edges=0;reg[31:0]rng=32'h617facd1;
 initial done=0;
 always @(negedge clk)begin
  cycles=cycles+1;
  if(cycles==3)rst_n=1;
  if(rst_n&&!done)begin
   rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
   we=(sent<2048)&&((cnt<DEPTH)||CAP_ATTACK)&&((rng&3)!=0);
   re=!CAP_ATTACK&&(sent>=DEPTH)&&(rng[7:4]!=0)&&ne;
   wd=word(sent);
   if(cnt==DEPTH)full_edges=full_edges+1;
  end else begin we=0;re=0;end
 end
 always @(posedge clk)if(rst_n&&!done)begin
  if(fault)begin
   if(!CAP_ATTACK)$fatal(1,"Unexpected FIFO fault W%0d",W);
   else begin $display("LANDING_OVERFLOW W%0d D%0d count%0d PASS",W,DEPTH,cnt);done=1;end
  end
  if(cnt>DEPTH)$fatal(1,"Invented logical capacity");
  if(we)sent=sent+1;
  if(re&&ne)begin
   if(rd!==word(received))$fatal(1,"FIFO data/order W%0d at%0d",W,received);
   received=received+1;
  end
  if(received==2048 && cnt==0)begin
   if(full_edges==0)$fatal(1,"No full queue coverage");
   $display("LANDING_FIFO W%0d D%0d accepted%0d returned%0d full_edges%0d cycles%0d PASS",W,DEPTH,sent,received,full_edges,cycles);done=1;
  end
  if(cycles>20000)$fatal(1,"FIFO timeout");
 end
endmodule
module tb_hbm_idx_landing_fifo_native #(parameter MUT=0);
 reg clk=0;always #5 clk=~clk;wire done0,done1,done2;
 native_fifo_case #(.W(1098),.AW(6))a(clk,done0);
 native_fifo_case #(.W(609),.AW(7))b(clk,done1);
 native_fifo_case #(.W(1098),.AW(6),.CAP_ATTACK(1),.MUT(MUT))c(clk,done2);
 always @(posedge clk)if(done0&&done1&&done2)$finish;
endmodule
