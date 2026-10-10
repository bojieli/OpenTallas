`timescale 1ns/1ps
module tb_hgi_coll_publish_tile;
 parameter integer MUT=0;
 reg clk=0,rst_n=0,push=0,pop=0;always #5 clk=~clk;
 reg[543:0]din=0;wire[662:0]encoded;wire valid,fault;wire[7:0]occupancy;
 integer sent=0,got=0,burst=0,cyc=0,first=-1,latency=0,checked=0;reg[543:0]gold[0:2047];
 reg[31:0]rng=32'h87654321;
 ot_hgi_coll_publish_tile #(.ENABLE(1),.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.push(push),.pop(pop),.din(din),
 .valid(valid),.encoded(encoded),.fault(fault),.occupancy(occupancy));
 function automatic[543:0]pattern(input integer n);
  begin for(integer w=0;w<17;w=w+1)pattern[w*32+:32]=32'hff810077^(32'(n)*32'h1234567)^32'(w*791);end
 endfunction
 always @(posedge clk)begin
  if(!rst_n)begin cyc=0;first=-1;end else begin
   cyc=cyc+1;if(push&&first<0)first=cyc;
   #1;if(valid&&latency==0)begin latency=cyc-first+1;if(latency!=7)$fatal(1,"tilefirsthead%0d",latency);end
  end
 end
 task reset;
  begin @(negedge clk);rst_n=0;push=0;pop=0;repeat(2)@(negedge clk);rst_n=1;sent=0;got=0;latency=0;end
 endtask
 task check;
  begin
   if(pop)begin
    if(!valid)$fatal(1,"fullratebubble");
    for(integer w=0;w<17;w=w+1)if(encoded[w*39+:32]!==gold[got][w*32+:32])$fatal(1,"tilepayloadword%0d index%0d",w,got);
    got=got+1;checked=checked+1;
   end
   if(push)begin gold[sent]=din;sent=sent+1;end
   @(posedge clk);#2;if(fault||integer'(occupancy)!=sent-got)$fatal(1,"tileoccupancy%0d vs%0d",occupancy,sent-got);
  end
 endtask
 initial begin
  reset();
  for(integer t=0;t<128;t=t+1)begin @(negedge clk);push=1;din=pattern(sent);check();end
  @(negedge clk);push=0;repeat(8)@(negedge clk);
  if(occupancy!=128||dut.core_count!=126||!dut.pi||!valid)$fatal(1,"tilecapacity composition");
  for(integer t=0;t<128;t=t+1)begin @(negedge clk);pop=1;check();burst=burst+1;end
  @(negedge clk);pop=0;
  for(integer t=0;t<500;t=t+1)begin
   @(negedge clk);rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   pop=valid&&rng[1];push=(occupancy<128||pop)&&rng[4];din=pattern(sent);check();
  end
  while(got<sent)begin @(negedge clk);push=0;pop=valid;check();end
  @(negedge clk);push=0;pop=0;repeat(8)@(negedge clk);
  if(occupancy||valid||dut.core_count)$fatal(1,"contextnotdrained");
  @(negedge clk);dut.ovi=0;#1;if(valid||!fault)$fatal(1,"egresscontrol corruption");
  @(posedge clk);#2;if(!fault)$fatal(1,"egressfaultnotsticky");
  reset();@(negedge clk);dut.core.faulti=0;#1;if(valid||!fault)$fatal(1,"corefaultflag unprotected");
  @(posedge clk);#2;if(!fault)$fatal(1,"coreflagfaultnotsticky");
  reset();@(negedge clk);dut.badi=0;#1;if(valid||!fault)$fatal(1,"tilefaultflag unprotected");
  @(posedge clk);#2;if(!fault)$fatal(1,"tileflagfaultnotsticky");
  reset();@(negedge clk);dut.pii=0;#1;if(valid||!fault)$fatal(1,"rawPIvalid unprotected");
  @(posedge clk);#2;if(!fault)$fatal(1,"rawPIflagfaultnotsticky");
  $display("PASS protected publisher tile popped=%0d fullrate=%0d firsthead7 total128 drain/control; rawPIcapture encodedoutputpinflops",checked,burst);
  $finish;
 end
endmodule
