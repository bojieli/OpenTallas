`timescale 1ns/1ps
// Independent age check: every output bit equals the input of exactly INJ_COPY_EDGES=1 edge earlier, rd and addr
// together; rd is 0 out of reset. Random addresses, rd patterns covering 00/01/10/11.
module tb_hgi_coll_inj_copy;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0;reg [159:0] a=0;reg [1:0] r=0;wire [159:0] ao;wire [1:0] ro;
 reg [159:0] ea;reg [1:0] er;integer checks=0,bad=0,cov[0:3];
 ot_hgi_coll_inj_copy dut(.clk(clk),.rst_n(rst_n),.inj_addr_i(a),.inj_rd_i(r),.inj_addr_o(ao),.inj_rd_o(ro));
 initial begin
  for(integer k=0;k<4;k=k+1)cov[k]=0;
  repeat(3)@(negedge clk);
  if(ro!==2'b00)bad=bad+1;
  rst_n=1;
  for(integer c=0;c<4000;c=c+1)begin
   @(negedge clk);
   ea=a;er=r;
   for(integer w=0;w<5;w=w+1)a[w*32+:32]=$random;
   r=$random;
   #0.1;                                  // new input applied, edge not yet taken: output still holds the old word
   checks=checks+1;cov[er]=cov[er]+1;
   if(c>0 && (ao!==ea||ro!==er))bad=bad+1;
   @(posedge clk);#0.1;                   // one edge later every bit (addr and rd) carries the new word
   checks=checks+1;
   if(ao!==a||ro!==r)bad=bad+1;
  end
  for(integer k=0;k<4;k=k+1)begin $display("INJCOPY rd%0d seen%0d",k,cov[k]);if(cov[k]==0)bad=bad+1;end
  if(bad!=0)$fatal(1,"INJCOPY FAIL mismatches%0d checks%0d",bad,checks);
  $display("INJCOPY PASS checks%0d bits162 age1",checks);$finish;
 end
endmodule
