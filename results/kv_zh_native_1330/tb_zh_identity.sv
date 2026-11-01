`timescale 1ns/1ps
module tb_zh_identity;
parameter MUT=0;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,start=0,zg=0; reg [127:0] zs_we=0,sid=0; reg [3:0] ziv=0; reg [5:0] zp=0;
wire [63:0] a,b; wire [3:0] ae,be;
retained_zh gold(.clk(clk),.rst_n(rst_n),.start(start),.zs_we(zs_we),.sid(sid),.ziv(ziv),.zg(zg),.zp(zp),.root(a),.zerr(ae));
ot_nhb_zh dut(.clk(clk),.rst_n(rst_n),.start(start),.zs_we(zs_we),.sid(sid),.ziv(ziv),.zg(zg),.zp(zp),.root(b),.zerr(be));
integer i,n=0,defined=0,err=0; reg [31:0] rng=32'h12345678;
initial begin
 for(i=0;i<640;i=i+1) begin
  @(negedge clk); rng=(rng^ (rng<<13));rng=(rng^(rng>>17));rng=(rng^(rng<<5));
  rst_n=(i>=8)&&!(i>=333&&i<339);start=(i%151==10);zg=i[0];zp=i[5:0];ziv=(i%3==0)?4'b1111:4'b0000;
  sid={rng,rng^32'h3f800000,rng+32'h40000000,rng^32'h80000000};
  zs_we=(i%5==0)?128'b0:~128'b0;
  @(posedge clk);#1;
  if(i>=10) begin
   n=n+1;if((^{a,ae})!==1'bx)defined=defined+1;
   if({a,ae}!=={b^MUT,be})err=err+1;
  end
 end
 $display("ZH_NATIVE_LOCKSTEP count=%0d defined=%0d err=%0d MUT=%0d",n,defined,err,MUT);
 if(err!=0||defined<200)$fatal(1,"ZH native identity gate");$finish;
end
endmodule
