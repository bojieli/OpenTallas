`timescale 1ns/1ps
module tb_pinret_flow;
 parameter integer MUT=0;
 reg clk=0,rst_n=0; always #0.5 clk=~clk;
 reg in_valid=0,out_ready=0; wire in_ready,out_valid;
 reg [4104:0] in_data; wire [4104:0] out_data;
 integer sent=0,received=0,cyc=0,first_out=-1,last_out=-1;
 reg held=0; reg [4104:0] snapshot;
 function [4104:0] payload(input integer ordinal);
  for(integer b=0;b<4105;b=b+1) payload[b]=((ordinal*65537+(b/32)*7919)>>(b%32))&1;
 endfunction
 ot_fence_pin_return #(.W(4105),.MUT_RETURN(MUT)) dut(.*);
 always @(negedge clk) if(rst_n) begin
  in_valid=(sent<512); in_data=payload(sent);
  out_ready=(cyc%137>=64);
 end
 always @(posedge clk) if(rst_n) begin
  cyc=cyc+1;
  if(held && (!out_valid || snapshot!==out_data)) $fatal(1,"PINRET_FLOW_HELD_CHANGED");
  held=out_valid&&!out_ready; snapshot=out_data;
  if(in_valid&&in_ready) sent=sent+1;
  if(out_valid&&out_ready) begin
   if(out_data!==payload(received)) $fatal(1,"PINRET_FLOW_WRONG_OR_DUPLICATE received=%0d",received);
   if(received>=sent) $fatal(1,"PINRET_FLOW_UNISSUED");
   if(first_out<0) first_out=cyc; last_out=cyc;
   received=received+1;
  end
  if(received==512) begin
   $display("PINRET_FLOW PASS sent=%0d received=%0d cycles=%0d first=%0d last=%0d",sent,received,cyc,first_out,last_out);
   $finish;
  end
  if(cyc>10000) $fatal(1,"PINRET_FLOW_TIMEOUT");
 end
 initial begin repeat(4) @(negedge clk); rst_n=1; end
endmodule
