module tb;
reg clk=0,rst_n=1;reg[31:0] native_d=0;wire[31:0] tick,shadow;integer diff=0,resets=0;
tkshadow_formal dut(.*);
always #2 clk=~clk;
initial begin
 #1;rst_n=0;
 for(integer n=0;n<20000;n=n+1)begin
  @(negedge clk);rst_n=(n%149!=0)&&($urandom_range(0,999)!=0);native_d=$urandom;
  @(posedge clk);#1;if(!rst_n)resets=resets+1;
  if(shadow!==(tick-32'd153))diff=diff+1;
 end
 $display("TKM_SHADOW_LOCKSTEP cycles20000 differences%0d resetedges%0d",diff,resets);
`ifdef MUTANT
 if(diff==0)$fatal(1,"mutant escaped");
`else
 if(diff!=0)$fatal(1,"positive differed");
`endif
 $finish;
end
endmodule
