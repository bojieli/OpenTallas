`timescale 1ns/1ps
`default_nettype none
// Unit bench: a 3-level tree of ot_hgi_f20_relay4 (1 -> 4 -> 16 -> 64 leaves) driven by random F20 frames; every leaf
// must equal the host frame exactly 2*3 = 6 edges later, every edge. +N=edges, +MUT=0/1/2 (mutant in node [1][2]).
module tb_hgi_f20_relay4;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0; reg [319:0] host;
 wire [319:0] l1[0:3]; wire [319:0] l2[0:15]; wire [319:0] l3[0:63];
 ot_hgi_f20_relay4 r0(.clk(clk),.rst_n(rst_n),.fi(host),.o0(l1[0]),.o1(l1[1]),.o2(l1[2]),.o3(l1[3]));
 for (genvar a=0;a<4;a=a+1) begin:g1
  if (a==1) begin:gm
`ifdef MUTSEL
   ot_hgi_f20_relay4 #(.MUT(`MUTSEL)) r(.clk(clk),.rst_n(rst_n),.fi(l1[a]),.o0(l2[a*4]),.o1(l2[a*4+1]),.o2(l2[a*4+2]),.o3(l2[a*4+3]));
`else
   ot_hgi_f20_relay4 r(.clk(clk),.rst_n(rst_n),.fi(l1[a]),.o0(l2[a*4]),.o1(l2[a*4+1]),.o2(l2[a*4+2]),.o3(l2[a*4+3]));
`endif
  end else begin:gn
   ot_hgi_f20_relay4 r(.clk(clk),.rst_n(rst_n),.fi(l1[a]),.o0(l2[a*4]),.o1(l2[a*4+1]),.o2(l2[a*4+2]),.o3(l2[a*4+3]));
  end
 end
 for (genvar b=0;b<16;b=b+1) begin:g2
  ot_hgi_f20_relay4 r(.clk(clk),.rst_n(rst_n),.fi(l2[b]),.o0(l3[b*4]),.o1(l3[b*4+1]),.o2(l3[b*4+2]),.o3(l3[b*4+3]));
 end
 reg [319:0] hist[0:6];
 integer n, bad=0, chk=0, frames=0;
 always @(posedge clk) begin hist[0]<=host; for(integer h=1;h<=6;h=h+1) hist[h]<=hist[h-1]; end
 initial begin
  if(!$value$plusargs("N=%d",n)) n=3000;
  host=0; repeat(3) @(negedge clk); rst_n=1;
  for (integer c=0;c<n;c=c+1) begin
   @(negedge clk);
   for (integer w=0;w<10;w=w+1) host[w*32+:32]=$random;
   if (c%3==0) begin host[0]=1'b0; host[277]=1'b0; host[319]=1'b0; end else frames=frames+1;
   #0.5;
   if (c>8) for (integer l=0;l<64;l=l+1) begin chk=chk+1; if (l3[l]!==hist[5]) begin bad=bad+1; if(bad<4) $display("MISMATCH edge%0d leaf%0d",c,l); end end
  end
  if (bad==0) $display("F20_RELAY_TREE PASS checks%0d frames%0d latency6", chk, frames);
  else $display("F20_RELAY_TREE FAIL mismatches%0d checks%0d", bad, chk);
  $finish;
 end
endmodule
`default_nettype wire
