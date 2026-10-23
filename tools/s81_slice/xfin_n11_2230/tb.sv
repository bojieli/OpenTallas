`timescale 1ns/1ps
module pair #(parameter integer T=1,R=0,PB=0)(input wire[719:0]a,b,input wire[479:0]d,output wire bad);
 wire[38:0] wp,refwp;wire[63:0]wm;wire[63:0]refmask;
 ot_s81dv_finish_leafw #(.TREES(T),.R(R),.PB(PB)) u(.da(a[T*240-1:0]),.db(b[T*240-1:0]),.id(d),.wp(wp),.wm(wm));
 leafw_n10_reference #(.TREES(T),.R(R),.PB(PB)) r(.da(a[T*240-1:0]),.db(b[T*240-1:0]),.id(d),.wp(refwp));
 for(genvar i=0;i<64;i=i+1)assign refmask[i]=refwp[38]&&(refwp[32]==(i>=32));
 assign bad=(wp!==refwp)||(wm!==refmask);
endmodule
module tb;
 reg[719:0]a,b;reg[479:0]d;wire[29:0]bad;integer i,j;reg[31:0]rng=32'h8e72345f;
 function automatic[31:0]step(input[31:0]x);step=(x^(x<<13))^((x^(x<<13))>>17);endfunction
 for(genvar t=0;t<2;t=t+1)for(genvar p=0;p<3;p=p+1)for(genvar r=0;r<5;r=r+1)pair #(.T(t?3:1),.PB(p),.R(r))u(.a(a),.b(b),.d(d),.bad(bad[t*15+p*5+r]));
 initial begin
 for(i=0;i<3000;i=i+1)begin
  for(j=0;j<22;j=j+1)begin rng=step(rng);a[j*32+:32]=rng;end
  for(j=0;j<22;j=j+1)begin rng=step(rng);b[j*32+:32]=rng;end
  for(j=0;j<15;j=j+1)begin rng=step(rng);d[j*32+:32]=rng;end
  a[719:704]=rng[15:0];b[719:704]=~rng[15:0];
  if(i<240)begin a=0;b=0;a[i]=1;b[i]=1;end
  if(i==240)begin a=0;b=0;end
  #1;
  if(|bad)$fatal(1,"XFIN_N11_WRITE_MISMATCH case=%0d bad=%h",i,bad);
 end
 $display("XFIN_N11_WRITE_PASS cases=3000 profiles=30 comparisons=90000");$finish;
 end
endmodule
