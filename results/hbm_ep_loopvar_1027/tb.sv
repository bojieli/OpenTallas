`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0; always #1 clk=~clk;
reg [511:0] beat=0;wire [7:0] dr={8{!beat[1]}};
wire gv,nv,mv,gl,nl,ml,gf,nf,mf;wire [611:0] gd,nd,md;
ep_rx_gold #(.MUT(0)) gold(clk,rst_n,beat,dr,gv,gd,gl,gf);
ep_rx_gate #(.MUT(0)) gate(clk,rst_n,beat,dr,nv,nd,nl,nf);
ep_rx_gate #(.MUT(2)) mut(clk,rst_n,beat,dr,mv,md,ml,mf);
integer n,k,phase=0,checks=0,bad=0,mutbad=0;reg [31:0] rnd=32'h19283746;reg idle;
initial begin
 repeat(5) @(negedge clk);rst_n=1;
 for(n=0;n<4096;n=n+1)begin
  @(negedge clk);
  for(k=0;k<16;k=k+1)begin rnd=rnd^(rnd<<13);rnd=rnd^(rnd>>17);rnd=rnd^(rnd<<5);beat[k*32+:32]=rnd;end
  idle=(n%7==6);beat[1]=idle;beat[0]=(!idle && phase==0);if(!idle)phase=(phase+1)%5;
  @(posedge clk);#0.1;
  checks=checks+1;
  if({gv,gd,gl,gf}!=={nv,nd,nl,nf})begin bad=bad+1;if(bad<5)$display("DIFF n=%0d",n);end
  if({gv,gd,gl,gf}!=={mv,md,ml,mf})mutbad=mutbad+1;
 end
 $display("EP_RX_LOOPFIX checks=%0d errors=%0d mutant_mismatches=%0d",checks,bad,mutbad);
 if(bad!=0 || mutbad==0)$fatal(1,"lockstep or negative control failed");
 $finish;
end
endmodule
