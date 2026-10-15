`timescale 1ns/1ps
module tb_idx_meta_delay;
 parameter integer MUT=0;
 reg clk=0,rst_n=0; reg [24:0] d=0;
 wire [24:0] q;
 if(MUT==0)begin : g_actual
  hidx_meta_w25_d123_r0 dut(.*);
 end else begin : g_mutant
  ot_hdc_delay #(.W(25),.D(MUT==1?122:123),.RESET(MUT==2?1:0)) dut(.*);
 end
 wire [24:0] q_reference;
 ot_hdc_delay #(.W(25),.D(123),.RESET(0)) reference(.clk(clk),.rst_n(rst_n),.d(d),.q(q_reference));
 reg [24:0] expected [0:799];
 integer errors=0, checks=0;
 reg [31:0] random_state=32'h183ac529;
 initial begin
  for(integer n=0;n<800;n=n+1)begin
   random_state=random_state ^ (random_state<<13);
   random_state=random_state ^ (random_state>>17);
   random_state=random_state ^ (random_state<<5);
   // Full port bits, including otherwise constant scorer metadata straps.
   d=random_state[24:0];expected[n]=d;
   rst_n=!(n<4 || n==300 || n==500);
   #5;clk=1;#1;
   if(n>=122)begin
    checks=checks+1;
    if(q!==expected[n-122] || q!==q_reference)errors=errors+1;
   end
   #4;clk=0;
  end
  $display("IDX_META_DELAY cycles=800 checks=%0d errors=%0d MUT=%0d",checks,errors,MUT);
  if(errors!=0)$fatal(1,"metadata exact delay mismatch");
  $finish;
 end
endmodule
