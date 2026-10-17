`timescale 1ns/1ps
module tb_hgi_coll_slice_v7;
 reg clk=0;always #1 clk=~clk;
 reg [1535:0] d1=0;wire [1535:0] d2,d3;reg [1535:0] e2=0,e3=0;
 reg [23:0] sel=0;reg [2047:0] rd=0;wire [2047:0] got;
 reg [23:0] history[0:8];reg [2047:0] prior=0,expected=0;
 integer checks=0,bad=0,coverage[0:7],n=2000;
 ot_hgi_coll_upipe_sliced_v7 u(.clk({16{clk}}),.d1(d1),.d2(d2),.d3(d3));
 ot_hgi_coll_vmasm_sliced_v7 v(.clk({16{clk}}),.sel(sel),.rd_il(rd),.as_il(got));
 // Independent bank-major expected payload. Different banks carry different tagged patterns.
 always @(posedge clk)begin
  e2<=d1;e3<=e2;
  for(integer pair=0;pair<4;pair=pair+1)for(integer half=0;half<2;half=half+1)
   for(integer bitno=0;bitno<256;bitno=bitno+1)
    expected[bitno*8+pair*2+half]<=prior[bitno*8+int'(history[8][pair*6+half*3+:3])];
  prior<=rd;history[0]<=sel;for(integer k=1;k<9;k=k+1)history[k]<=history[k-1];
 end
 initial begin
  for(integer b=0;b<8;b=b+1)coverage[b]=0;
  for(integer c=0;c<n;c=c+1)begin
   @(negedge clk);
   if(c>12)begin
    checks=checks+1;
    if(d2!==e2||d3!==e3||got!==expected)bad=bad+1;
    for(integer k=0;k<8;k=k+1)coverage[history[8][k*3+:3]]=coverage[history[8][k*3+:3]]+1;
   end
   for(integer w=0;w<48;w=w+1)d1[w*32+:32]=$random;
   for(integer p=0;p<8;p=p+1)sel[p*3+:3]=(c+p)%8;
   for(integer i=0;i<256;i=i+1)for(integer bank=0;bank<8;bank=bank+1)
    rd[i*8+bank]=((i+3*c)>>(bank%5)) ^ bank ^ (c>>(bank%3));
  end
  for(integer b=0;b<8;b=b+1)begin
   $display("SLICE_V7 bank%0d selected%0d",b,coverage[b]);if(coverage[b]==0)bad=bad+1;
  end
  if(bad!=0)$fatal(1,"SLICE_V7 FAIL mismatches%0d checks%0d",bad,checks);
  $display("SLICE_V7 PASS checks%0d bits_per_check6144",checks);$finish;
 end
endmodule
