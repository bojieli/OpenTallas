`timescale 1ns/1ps
module tb_unknown;
 reg clk=0,rn=1,src=1,h=1;
 wire known;wire[31:0]errors;
 always #5 clk=~clk;
 always @(posedge clk) h<=src;
 kva_authority_path #(.DEPTH(1)) mon(.clk(clk),.source_rst_n(rn),.source_valid(src),.source_alias(src),.hop_q(h),.known(known),.errors(errors));
 initial begin
   #2;rn=0;src=0;
   #1;rn=1;
   @(negedge clk);#0.002;
   if(!known || errors) $fatal(1,"UNKNOWN_CONTROL_FAIL healthy frontier");
   #1;src=1'bx;
   @(negedge clk);#0.002;
   if(errors==0) $fatal(1,"UNKNOWN_CONTROL_FAIL authoritative X ignored");
   $display("AUTHORITY_UNKNOWN_CONTROL_PASS");$finish;
 end
endmodule
