`timescale 1ns/1ps
module tb_static_correction;
reg [5439:0] cw;reg[549:0] ev;reg[54:0]hit;reg[3:0]cc;
wire[5439:0]ncw;wire[5:0]nr_add;
ot_hbm_kp4_correction55_static dut(.*);
reg[5439:0]refcw;reg[5:0]refnr;reg[31:0]rng=32'hbedabeda;
integer phase,v,b,k,e,checked=0;
task verify;
begin
 #1;refcw=cw;refnr=0;
 for(k=0;k<55;k=k+1)begin
  e=55*cc+k;
  if(e<544 && hit[k])begin refcw[10*e+:10]=refcw[10*e+:10]^ev[k*10+:10];refnr=refnr+1;end
 end
 if(ncw!==refcw || nr_add!==refnr)$fatal(1,"static correction mismatch phase=%0d vector=%0d",cc,v);
 checked=checked+1;
end endtask
initial begin
 for(phase=0;phase<16;phase=phase+1)begin
  cc=phase;cw=0;hit='1;ev=0;
  for(v=0;v<550;v=v+1)begin ev=0;ev[v]=1;verify;end
  ev='1;
  for(v=0;v<55;v=v+1)begin hit=0;hit[v]=1;verify;end
  for(v=0;v<64;v=v+1)begin
   for(b=0;b<5440;b=b+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);cw[b]=rng[0];end
   for(b=0;b<550;b=b+1)ev[b]=cw[b];
   hit=cw[54:0];verify;
  end
 end
 ev=0;hit='1;
 for(v=0;v<5440;v=v+1)begin cc=v%16;cw=0;cw[v]=1;verify;end
 $display("PASS static correction vectors=%0d all16phases ev/hit/CW basis +random",checked);$finish;
end
endmodule
