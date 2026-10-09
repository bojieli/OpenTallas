`timescale 1ns/1ps
module tb_markov_fault;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,iv=0,ordy=0;
 reg [31:0] head=0;
 reg [255:0] w=0,x=0;
 wire sr,ir,ov,fault;
 wire [31:0] bits;
 integer mode,b;
 ot_dsrom_markov_row dut(.clk(clk),.rst_n(rst_n),.start(start),.start_ready(sr),.head_logit(head),
  .in_valid(iv),.in_ready(ir),.weight_bf16(w),.embed_bf16(x),.out_valid(ov),.out_ready(ordy),.out_bits(bits),.fault(fault));
 initial begin
  for(mode=0;mode<3;mode=mode+1) begin
   rst_n=0;start=0;iv=0;w=0;x=0;head=0;repeat(4) @(negedge clk);rst_n=1;
   start=1;if(mode==0)head=32'h7f800000;
   @(negedge clk);start=0;
   for(b=0;b<16;b=b+1) begin
    iv=1;x={16{16'h3f80}};w={16{16'h3f80}};
    if(mode==1 && b==5) w[15:0]=16'h7fc0;
    if(mode==2 && b==2)start=1;else start=0;
    @(negedge clk);
   end
   iv=0;start=0;repeat(220) @(negedge clk);
   if(!fault || ov || sr) $fatal(1,"not fail-closed mode=%0d fault=%b valid=%b ready=%b",mode,fault,ov,sr);
  end
  $display("PASS faultcases nonfinite head/nonfinite product/overlapping start");$finish;
 end
endmodule
