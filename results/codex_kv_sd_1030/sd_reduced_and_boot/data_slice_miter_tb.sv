module tb;
reg clk=0;always #5 clk=~clk;
reg tr=0,rr=0,d=0;reg[5:0]k=0;wire q0,q1,r0,r1,f0,f1;integer i,j,m=0,c=0;reg[31:0]rng=32'h519ac730;
ot_dp_clk_landing_cas #(.W(1),.DEPTH(4)) a(clk,tr,clk,rr,k,d,q0,r0,f0);
ot_dp_clk_landing_cas_small #(.W(1),.DEPTH(4)) b(clk,tr,clk,rr,k,d,q1,r1,f1);
initial begin
 for(j=0;j<64;j=j+1)begin
  @(negedge clk);tr=0;rr=0;k=j;repeat(12)@(negedge clk);
  for(i=0;i<256;i=i+1)begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};d=rng[0];tr=(i%83>7);rr=(i%83>10);
   @(posedge clk);#1;
   if({q0,r0,f0}!=={q1,r1,f1})m=m+1;c=c+1;
   @(negedge clk);
  end
 end
 $display("DATA_SLICE_NATIVE_COMPARE cases64 cycles%0d mismatch%0d",c,m);if(m)$fatal(1,"data slice changed native status/data");$finish;
end
endmodule
