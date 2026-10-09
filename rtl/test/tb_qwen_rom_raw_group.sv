`timescale 1ns/1ps
module tb_qwen_rom_raw_group;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg [2559:0] cap=0;reg [4:0] sel=0;
 wire [1023:0] q;
 ot_qwen_rom_raw_group #(.MUT(MUT)) a(.clk(clk),.cap(cap[1279:0]),.sel(sel),.q(q[511:0]));
 ot_qwen_rom_raw_group #(.MUT(MUT)) b(.clk(clk),.cap(cap[2559:1280]),.sel(sel),.q(q[1023:512]));
 function automatic [15:0] golden(input integer c);
  integer n,e,t,m;
  begin
   n=(c>=128)?256-c:c;e=0;t=n;
   while(t>=2) begin e=e+1;t=t/2;end
   m=(n-(1<<e))<<(7-e);
   golden=(n==0)?0:((c>=128?32768:0)|((127+e)<<7)|m);
  end
 endfunction
 reg [1023:0] ex[0:2];reg [1023:0] now;
 integer cycle,bank,lane,pair,c,selected,checks=0;
 initial begin
  ex[0]=0;ex[1]=0;ex[2]=0;
  for(cycle=0;cycle<4096;cycle=cycle+1) begin
   @(negedge clk);
   selected=cycle%5;sel=(cycle%11==0)?0:(1<<selected);now=0;
   for(pair=0;pair<2;pair=pair+1)
    for(bank=0;bank<5;bank=bank+1)
     for(lane=0;lane<32;lane=lane+1) begin
      c=(cycle+bank*37+lane*13+pair*83)&255;
      cap[(pair*5+bank)*256+lane*8+:8]=c;
      if(sel[bank]) now[pair*512+lane*16+:16]=golden(c);
     end
   @(posedge clk);
   ex[2]=ex[1];ex[1]=ex[0];ex[0]=now;
   #1;
   if(cycle>=2) begin
    checks=checks+64;
    if(q!==ex[2]) begin $display("FAIL raw_group cycle=%0d expected=%h actual=%h",cycle,ex[2],q);$finish;end
   end
  end
  $display("PASS raw_group full_shape columns=2 banks=5 codes_per_bank=32 all256_int8 bank_changes_and_bubbles cycles=4096 checks=%0d latency_edges=3",checks);
  $finish;
 end
endmodule
