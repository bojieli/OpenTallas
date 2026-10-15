`timescale 1ns/1ps
module tb_chien_linear;
`include "ot_s81_gf1024.svh"
reg [469:0] x;wire[2199:0] y;wire[469:0] step;
ot_hbm_kp4_chien55_map dut(.x(x),.y(y),.step(step));
reg [9:0] coeff[0:54][0:29];reg[9:0] xp[0:54];reg[9:0] back[0:46];
reg[9:0] lv,ov,dv,xe;integer v,k,i,b;reg[31:0] rng=32'h9e3779b9;
initial begin
 for(k=0;k<55;k=k+1)begin
  xp[k]=gf_alpha(k);
  for(i=0;i<30;i=i+1)coeff[k][i]=gf_alpha(-i*k);
 end
 for(i=0;i<47;i=i+1)back[i]=i<46?gf_alpha(-(i<16?i:i-16)*55):gf_alpha(55);
 for(v=0;v<535;v=v+1)begin
  x=0;
  if(v<470)x[v]=1'b1;
  else if(v>470)for(b=0;b<470;b=b+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);x[b]=rng[0];end
  #1;
  for(k=0;k<55;k=k+1)begin
   lv=0;ov=0;dv=0;
   for(i=0;i<16;i=i+1)lv=lv^gf_mul(x[i*10+:10],coeff[k][i]);
   for(i=0;i<30;i=i+1)ov=ov^gf_mul(x[160+i*10+:10],coeff[k][i]);
   for(i=1;i<16;i=i+2)dv=dv^gf_mul(x[i*10+:10],coeff[k][i]);
   xe=gf_mul(x[460+:10],xp[k]);
   if(y[k*40+:40]!=={xe,dv,ov,lv})$fatal(1,"Chien map mismatch vector=%0d k=%0d",v,k);
  end
  for(i=0;i<47;i=i+1)if(step[i*10+:10]!==gf_mul(x[i*10+:10],back[i]))$fatal(1,"Chien step mismatch vector=%0d i=%0d",v,i);
 end
 $display("PASS Chien linear 470 basis + zero + 64 random; 2670 output bits/vector");$finish;
end
endmodule
