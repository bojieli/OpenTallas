`timescale 1ns/1ps
module tb;
reg [5:0] ck=0; reg [69:0] data[0:5]; wire [5:0] fa,fb; wire [69:0] da[0:5],db[0:5];
reg [69:0] ea[0:5]; integer seen[0:5];integer checks=0;integer n,l,b;reg [31:0] rng=32'h6c616e65;
dsfd_stnv_70x6_proof a(.fi0(ck[0]),.di0(data[0]),.fo0(fa[0]),.do0(da[0]),.fi1(ck[1]),.di1(data[1]),.fo1(fa[1]),.do1(da[1]),.fi2(ck[2]),.di2(data[2]),.fo2(fa[2]),.do2(da[2]),.fi3(ck[3]),.di3(data[3]),.fo3(fa[3]),.do3(da[3]),.fi4(ck[4]),.di4(data[4]),.fo4(fa[4]),.do4(da[4]),.fi5(ck[5]),.di5(data[5]),.fo5(fa[5]),.do5(da[5]));
dsfd_stnv_70x6_proof u_second(.fi0(fa[0]),.di0(da[0]),.fo0(fb[0]),.do0(db[0]),.fi1(fa[1]),.di1(da[1]),.fo1(fb[1]),.do1(db[1]),.fi2(fa[2]),.di2(da[2]),.fo2(fb[2]),.do2(db[2]),.fi3(fa[3]),.di3(da[3]),.fo3(fb[3]),.do3(db[3]),.fi4(fa[4]),.di4(da[4]),.fo4(fb[4]),.do4(db[4]),.fi5(fa[5]),.di5(da[5]),.fo5(fb[5]),.do5(db[5]));

genvar g; generate for(g=0;g<6;g=g+1) begin:lane
 initial begin #(0.1*g);forever #4.166 ck[g]=~ck[g];end
 always @(negedge ck[g])begin
  ea[g]=data[g];seen[g]=1;#0.001;
  if(da[g]!==ea[g]||fa[g]!==~ck[g])$fatal(1,"RETURN_BUNDLE FAIL first edge lane=%0d",g);checks=checks+1;
 end
 always @(posedge ck[g])begin
  #0.001;if(seen[g])begin
   if(db[g]!==ea[g]||fb[g]!==ck[g])$fatal(1,"RETURN_BUNDLE FAIL second edge lane=%0d",g);checks=checks+1;
  end
 end
end endgenerate
initial begin
 for(l=0;l<6;l=l+1)begin data[l]=0;seen[l]=0;ea[l]=0;end
 for(n=0;n<2188;n=n+1)begin
  #17;
  for(l=0;l<6;l=l+1)begin
   if(n<140)begin data[l]=(n<70)?70'b0:{70{1'b1}};data[l][n%70]=(n<70);data[l][(n+7*l)%70]=~data[l][(n+7*l)%70];end
   else for(b=0;b<70;b=b+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);data[l][b]=rng[0];end
  end
 end
 #20;if(checks<50000)$fatal(1,"RETURN_BUNDLE FAIL coverage %0d",checks);
 $display("RETURN_BUNDLE PASS lanes=6 bits=70 depth=2 checks=%0d",checks);$finish;
end
endmodule
