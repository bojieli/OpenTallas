`timescale 1ns/1ps
module tb_hbm_attn_bank_gather_binary;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cv=0;reg[2047:0]td=0;reg[63:0]tf=0;reg[2:0]sel=0;
 wire[255:0]by,old_by;wire[7:0]bf,old_bf;wire ov,old_ov;
 ot_hbm_attn_pv_bank_gather_binary dut(clk,rst_n,cv,td,tf,sel,by,bf,ov);
 ot_hbm_attn_pv_bank_gather_registered baseline(clk,rst_n,cv,td,tf,sel,old_by,old_bf,old_ov);
 reg pv=0;reg[263:0]expected=0;integer cycle,g,d,checks=0;
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  for(cycle=0;cycle<5002;cycle=cycle+1)begin
   @(negedge clk);
   cv=cycle<5000&&(cycle%5!=0);sel=3'(cycle%8);
   for(g=0;g<8;g=g+1)begin
    tf[g*8+:8]=8'((cycle*11)^(g*37));
    for(d=0;d<8;d=d+1)td[g*256+d*32+:32]=32'((cycle<<16)^(g<<8)^(d*31));
   end
   @(posedge clk);#1;
   if(ov!==pv||ov!==old_ov)$fatal(1,"valid alignment cycle%0d",cycle);
   if(pv)begin
    if({bf,by}!==expected)$fatal(1,"binary payload/flags cycle%0d",cycle);
    if({bf,by}!=={old_bf,old_by})$fatal(1,"baseline equivalence cycle%0d",cycle);
    checks=checks+264;
   end
   pv=cv;expected={tf[sel*8+:8],td[sel*256+:256]};
  end
  $display("PASS BANK_GATHER_BINARY checks=%0d full_rate_and_bubbles same2edges",checks);
  $finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
