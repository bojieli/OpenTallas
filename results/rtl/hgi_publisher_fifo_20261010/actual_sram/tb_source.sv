`timescale 1ns/1ps
module tb_hgi_coll_publish_fifo;
 parameter integer MUT=0;
 reg clk=0,rst_n=0,push=0,pop=0;always #5 clk=~clk;
 reg[543:0]din=0;wire[543:0]dout;wire valid,corrected,fault;wire[7:0]occupancy;
 integer sent=0,got=0,checks=0,burst=0,macro_corrected=0;reg[543:0]gold[0:2047];
 reg[31:0]rng=32'h12345678;
 ot_hgi_coll_publish_fifo #(.ENABLE(1),.MUT(MUT))dut(
  .clk(clk),.rst_n(rst_n),.push(push),.pop(pop),.din(din),.valid(valid),.dout(dout),
  .corrected(corrected),.fault(fault),.occupancy(occupancy));
 function automatic[543:0]pattern(input integer n);
  begin for(integer w=0;w<17;w=w+1)pattern[w*32+:32]=32'h7fc10000^(32'(n)*32'h1234567)^32'(w*701);end
 endfunction
 task reset;
  begin @(negedge clk);rst_n=0;push=0;pop=0;repeat(2)@(negedge clk);rst_n=1;sent=0;got=0;end
 endtask
 task edgecheck;
  begin
   if(pop)begin
    if(!valid||dout!==gold[got])$fatal(1,"payload/order mismatch got=%0d",got);
    if(corrected)macro_corrected=macro_corrected+1;
    got=got+1;checks=checks+1;
   end
   if(push)begin gold[sent]=din;sent=sent+1;end
   @(posedge clk);#1;
   if(fault||integer'(occupancy)!=sent-got)$fatal(1,"fault/occupancy sent=%0d got=%0d occ=%0d",sent,got,occupancy);
  end
 endtask
 initial begin
  reset();
  for(integer t=0;t<128;t=t+1)begin @(negedge clk);push=1;pop=0;din=pattern(sent);edgecheck();end
  @(negedge clk);push=0;repeat(8)@(negedge clk);
  if(occupancy!=128||!valid)$fatal(1,"full128 shape missing");
  // Row127 has not been prefetched; inject in actual synchronous SRAM storage.
  dut.mem.g_m[0].u_sram.mem[127][0]=~dut.mem.g_m[0].u_sram.mem[127][0];
  // Warm prefetched heads must drain128 consecutive packets with actual SRAM.
  for(integer t=0;t<128;t=t+1)begin @(negedge clk);pop=1;edgecheck();burst=burst+1;end
  if(macro_corrected!=1)$fatal(1,"SRAM singlebit correction not exercised");
  @(negedge clk);pop=0;
  for(integer t=0;t<1000;t=t+1)begin
   @(negedge clk);rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   pop=valid&&rng[0];push=(occupancy<128||pop)&&rng[3];din=pattern(sent);edgecheck();
  end
  while(got<sent)begin @(negedge clk);push=0;pop=valid;edgecheck();end
  @(negedge clk);pop=0;push=1;din=pattern(sent);edgecheck();
  @(negedge clk);push=0;while(!valid)@(negedge clk);
  dut.head[dut.hp][0]=~dut.head[dut.hp][0];
  #1;if(!valid||!corrected||dout!==gold[got])$fatal(1,"singlebit correction failed");
  pop=1;edgecheck();@(negedge clk);pop=0;
  push=1;din=pattern(sent);edgecheck();@(negedge clk);push=0;while(!valid)@(negedge clk);
  dut.head[dut.hp][1:0]=dut.head[dut.hp][1:0]^2'b11;
  #1;if(valid)$fatal(1,"doublebit stillpublishable");
  @(posedge clk);#1;if(!fault)$fatal(1,"UE notsticky");
  reset();@(negedge clk);push=1;din=pattern(sent);edgecheck();
  @(negedge clk);push=0;@(posedge clk);#1;
  dut.mem.g_m[0].u_sram.mem[0][1:0]=dut.mem.g_m[0].u_sram.mem[0][1:0]^2'b11;
  repeat(7)@(negedge clk);if(!fault||valid)$fatal(1,"SRAM doublebit notfailclosed");
  reset();@(negedge clk);dut.wi=7'h00;#1;
  if(valid)$fatal(1,"controlcorruption publish");@(posedge clk);#1;if(!fault)$fatal(1,"pointercorruption notsticky");
  reset();@(negedge clk);dut.ti=8'h00;@(posedge clk);#1;if(!fault)$fatal(1,"countcorruption notsticky");
  reset();@(negedge clk);pop=1;@(posedge clk);#1;if(!fault)$fatal(1,"underflow notfaulted");
  reset();
  for(integer t=0;t<128;t=t+1)begin @(negedge clk);push=1;din=pattern(sent);edgecheck();end
  @(negedge clk);push=1;@(posedge clk);#1;if(!fault)$fatal(1,"overflow notfaulted");
  $display("PASS protected publisher FIFO checks=%0d fullrate_burst=%0d capacity128 SECDED/UE/pointer/overflow/underflow",checks,burst);
  $finish;
 end
endmodule
