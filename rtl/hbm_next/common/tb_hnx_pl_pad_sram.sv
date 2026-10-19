`timescale 1ns/1ps
module tb_hnx_pl_pad_sram #(parameter integer MUT=0);
 reg ck=0; always #5 ck=~ck;
 reg rst_n=0;
 reg [817:0] d;
 wire [817:0] q;
 reg [817:0] hist[0:2];
 integer t,j,k,age=0,checks=0,errors=0;
 hnx_pl_pad_sram #(.W(818),.N(3),.MUT(MUT)) dut(.*);
 initial begin
  d=0;
  for(t=0;t<1000;t=t+1) begin
   @(negedge ck);
   rst_n=(t>4 && !(t>=500 && t<507));
   for(j=0;j<818;j=j+1) d[j]=$urandom_range(0,1);
   @(posedge ck);
   if(rst_n) begin
    for(k=2;k>0;k=k-1) hist[k]=hist[k-1];
    hist[0]=d;
    age=age+1;
   end else age=0;
   #1;
   if(age>=3) begin
    checks=checks+1;
    if(q!==hist[2]) errors=errors+1;
   end
  end
  $display("HNXPAD %s checks=%0d errors=%0d",errors?"FAIL":"PASS",checks,errors);
  if(errors) $fatal(1,"HNXPAD mismatch");
  $finish;
 end
endmodule
