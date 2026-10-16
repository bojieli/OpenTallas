`timescale 1ns/1ps
module tb_return_plane;
parameter MUT=0;
reg ck=0; always #5 ck=~ck;
reg v5=0,v6=0,v7=0,si=0;
reg [23:0] a5=0,a6=0,a7=0;
reg [8191:0] d=0;
wire [2047:0] q;
reg [6143:0] pos;
reg [2559:0] win;
reg [2047:0] expected;
integer i,cycle,checks=0,errors=0;
genvar b,e,l;
for(b=0;b<32;b=b+1) begin:P
 wire [255:0] pd;
 wire [63:0] pq;
 for(e=0;e<256;e=e+1) assign pd[e]=d[e*32+b];
 ot_qfd_vm_su_return_plane #(.MUT(MUT)) dut(ck,v5,v6,v7,a5,a6,a7,si,pd,pq);
 for(l=0;l<64;l=l+1) assign q[l*32+b]=pq[l];
end
wire [3:0] r5=a5[4+:4],r6=a6[4+:4],off7=a7[3:0];
always @(posedge ck) begin
 if(v5) for(i=0;i<12;i=i+1) pos[i*512+:512]<=d[((i+(r5 & ~7))%16)*512+:512];
 if(v6) for(i=0;i<5;i=i+1) win[i*512+:512]<=pos[(i+(r6 & 7))*512+:512];
 if(v7) for(i=0;i<64;i=i+1) expected[i*32+:32]<=((a7+(si?i:0))<177808)?win[(off7+(si?i:0))*32+:32]:32'd0;
end
initial begin
 for(cycle=0;cycle<5000;cycle=cycle+1) begin
  @(negedge ck);
  for(i=0;i<256;i=i+1) d[i*32+:32]=$random;
  a5=$urandom_range(0,177840);a6=$urandom_range(0,177840);a7=$urandom_range(0,177840);
  // Sweep every byte offset/bank, scalar/broadcast, last-row boundary and independently idle stages.
  if(cycle%4==0) a7=177780+cycle%64;
  v5=(cycle<5)?1:$urandom_range(0,1);v6=(cycle<5)?1:$urandom_range(0,1);v7=(cycle<5)?1:$urandom_range(0,1);si=cycle%2;
  @(posedge ck);#1;
  if(cycle>5) begin checks=checks+1;if(q!==expected)errors=errors+1;end
 end
 if(errors) $fatal(1,"FAIL return plane checks=%0d errors=%0d",checks,errors);
 $display("PASS return plane checks=%0d",checks);$finish;
end
endmodule
