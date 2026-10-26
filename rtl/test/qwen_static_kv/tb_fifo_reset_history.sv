`timescale 1ps/1fs
module tb_fifo_reset_history #(parameter integer MUT=0);
 reg clk=0;always #416.5 clk=~clk;
 reg rst_n=1,wv=0,rr=0;reg[31:0]wd=0;
 wire wr,rv;wire[31:0]rd;wire ofl,ufl;
 ot_async_fifo #(.WIDTH(32),.DEPTH(8),.EXT_RST(1)) dut(clk,rst_n,wv,wr,wd,ofl,clk,rst_n,rv,rr,rd,ufl);
 integer sent=0,received=0;
 always @(posedge clk)if(rst_n&&rr)begin
  if(ofl||ufl)$fatal(1,"FIFO fault");
  if(rv)begin if(rd!==32'(received))$fatal(1,"FIFO order %0d %0d",rd,received);received++;end
 end
 initial begin
   // Upstream registered reset has not arrived at power on. Pointer history
   // assertions cannot compare independently randomized state in this interval.
   repeat(5)@(negedge clk);rst_n=0;
   repeat(5)@(negedge clk);rst_n=1;
   repeat(8)@(negedge clk);
   if(MUT==1)force dut.wr_gray=4'b1111;
   if(MUT==2)force dut.rd_gray=4'b1111;
   rr=1;
   while(sent<32)begin
     wv=wr;wd=sent;
     @(negedge clk);if(wv)sent++;
   end
   wv=0;
   repeat(10)@(negedge clk);
   if(received!=32)$fatal(1,"FIFO got %0d",received);
   $display("PASS random pre-reset FIFO then32words ordered");$finish;
 end
endmodule
