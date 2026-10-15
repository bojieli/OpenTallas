`timescale 1ns/1ps
module tb_static_gearbox;
 parameter integer MUT=0,F=612;
 localparam integer N=3*F;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,ts=0,rs=0,fv=0;
 reg [F-1:0] f=0;
 wire due,wv,rv,tf,rf;
 wire [486:0] w;
 wire [F-1:0] r;
 reg [F:0] tx[0:N-1],rx[0:N-1];
 string vec;
 integer k,e,checked=0;
 ot_hbm_static_gearbox_tx #(.F(F),.MUT(MUT==1?1:0)) t(clk,rst_n,ts,fv,f,due,wv,w,tf);
 ot_hbm_static_gearbox_rx #(.F(F),.MUT(MUT==2?2:0)) u(clk,rst_n,rs,wv,w,rv,r,rf);
 initial begin
  if(!$value$plusargs("VEC=%s",vec))$fatal(1,"missing VEC");
  $readmemh({vec,"/tx.hex"},tx);$readmemh({vec,"/rx.hex"},rx);
  for(e=0;e<2;e=e+1)begin
   @(negedge clk);rst_n=0;ts=0;rs=0;fv=0;
   repeat(3)@(posedge clk);
   @(negedge clk);rst_n=1;ts=1;
   @(posedge clk);#1;
   for(k=0;k<N;k=k+1)begin
    @(negedge clk);ts=0;rs=(k==0);fv=tx[k][F];f=tx[k][F-1:0];
    if(MUT==3 && k==19)fv=~fv;
    #1;if(due!==tx[k][F])$fatal(1,"TX calendar e%0d cycle%0d",e,k);
    @(posedge clk);#1;
    if(tf||rf)$fatal(1,"reservation fault e%0d cycle%0d",e,k);
    if(k>0)begin
     if(rv!==rx[k-1][F])$fatal(1,"RX calendar e%0d cycle%0d",e,k);
     if(rv)begin
      if(r!==rx[k-1][F-1:0])$fatal(1,"payload e%0d cycle%0d",e,k);
      checked=checked+1;
     end
    end
   end
   // Sample final pending transport word; next source frame starts a fresh
   // rational period. The following reset discards that new period explicitly.
   @(negedge clk);fv=tx[0][F];f=tx[0][F-1:0];
   @(posedge clk);#1;
   if(tf||rf||rv!==rx[N-1][F]||r!==rx[N-1][F-1:0])$fatal(1,"final frame");
   checked=checked+1;
  end
  if(checked!=2922)$fatal(1,"coverage %0d",checked);
  $display("PASS actualgearbox framebits=%0d wordbits=487 frames=%0d epochs=2 periods/epoch=3",F,checked);$finish;
 end
endmodule
