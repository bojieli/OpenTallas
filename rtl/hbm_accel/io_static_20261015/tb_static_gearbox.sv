`timescale 1ns/1ps
module tb_static_gearbox;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,ts=0,rs=0,fv=0;
 reg [611:0] f=0;
 wire due,wv,rv,tf,rf;
 wire [486:0] w;
 wire [611:0] r;
 reg [612:0] tx[0:1835],rx[0:1835];
 string vec;
 integer k,e,checked=0;
 ot_hbm_static_gearbox_tx #(.MUT(MUT==1?1:0)) t(clk,rst_n,ts,fv,f,due,wv,w,tf);
 ot_hbm_static_gearbox_rx #(.MUT(MUT==2?2:0)) u(clk,rst_n,rs,wv,w,rv,r,rf);
 initial begin
  if(!$value$plusargs("VEC=%s",vec))$fatal(1,"missing VEC");
  $readmemh({vec,"/tx.hex"},tx);$readmemh({vec,"/rx.hex"},rx);
  for(e=0;e<2;e=e+1)begin
   @(negedge clk);rst_n=0;ts=0;rs=0;fv=0;
   repeat(3)@(posedge clk);
   @(negedge clk);rst_n=1;ts=1;
   @(posedge clk);#1;
   for(k=0;k<1836;k=k+1)begin
    @(negedge clk);ts=0;rs=(k==0);fv=tx[k][612];f=tx[k][611:0];
    if(MUT==3 && k==19)fv=~fv;
    #1;if(due!==tx[k][612])$fatal(1,"TX calendar e%0d cycle%0d",e,k);
    @(posedge clk);#1;
    if(tf||rf)$fatal(1,"reservation fault e%0d cycle%0d",e,k);
    if(k>0)begin
     if(rv!==rx[k-1][612])$fatal(1,"RX calendar e%0d cycle%0d",e,k);
     if(rv)begin
      if(r!==rx[k-1][611:0])$fatal(1,"payload e%0d cycle%0d",e,k);
      checked=checked+1;
     end
    end
   end
   // Sample final pending transport word; next source frame starts a fresh
   // rational period. The following reset discards that new period explicitly.
   @(negedge clk);fv=tx[0][612];f=tx[0][611:0];
   @(posedge clk);#1;
   if(tf||rf||rv!==rx[1835][612]||r!==rx[1835][611:0])$fatal(1,"final frame");
   checked=checked+1;
  end
  if(checked!=2922)$fatal(1,"coverage %0d",checked);
  $display("PASS actual612/487gearbox frames=%0d epochs=2 periods/epoch=3",checked);$finish;
 end
endmodule
