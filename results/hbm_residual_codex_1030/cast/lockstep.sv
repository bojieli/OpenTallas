module cast_lockstep;
 reg [15:0] cs_r; reg [1:0] cj;
 wire [127:0] reference = {112'd0, cs_r + 16'(cj)};
 wire [15:0] scrd_index = cs_r + {14'd0, cj};
 wire [127:0] candidate = {112'd0, scrd_index};
 wire [127:0] mutant = {112'd0, scrd_index ^ 16'h1};
 integer a,b,count=0,detected=0;
 reg [15:0] special_cs[0:4]; reg [1:0] special_cj[0:6];
 initial begin
  for(a=0;a<65536;a=a+1)for(b=0;b<4;b=b+1)begin
   cs_r=a[15:0];cj=b[1:0];#1;
   if(reference!==candidate)$fatal(1,"mismatch %h %h %h %h",cs_r,cj,reference,candidate);
   if(reference!==mutant)detected=detected+1;
   count=count+1;
  end
  if(detected!=262144)$fatal(1,"mutant escaped");
  special_cs[0]=16'h0000;special_cs[1]=16'hffff;special_cs[2]=16'h5555;special_cs[3]=16'hxxxx;special_cs[4]=16'hzzzz;
  special_cj[0]=2'b00;special_cj[1]=2'b01;special_cj[2]=2'b10;special_cj[3]=2'b11;special_cj[4]=2'b0x;special_cj[5]=2'bx1;special_cj[6]=2'bzz;
  for(a=0;a<5;a=a+1)for(b=0;b<7;b=b+1)begin
   cs_r=special_cs[a];cj=special_cj[b];#1;
   if(reference!==candidate)$fatal(1,"four-state mismatch %h %h",cs_r,cj);
  end
  $display("PASS four-state35 X/Z/carry cases");
  $display("PASS exhaustive known-bit cast lockstep %0d combinations, mismatch0, mutantCAUGHT%0d, cycles_added0",count,detected);$finish;
 end
endmodule
