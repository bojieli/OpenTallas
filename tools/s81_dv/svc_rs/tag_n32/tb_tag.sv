`timescale 1ns/1ps
module tb_tag;
 reg clk=0;always #5 clk=~clk;
 reg[3:0]code;reg[255:0]sector,held;reg[31:0]rng=32'h219cfa;wire[143:0]one,two;
 tag_gate dut(.clk(clk),.code(code),.sector(sector),.held(held),.one(one),.two(two));
 integer checks=0,errors=0;reg[511:0]v;reg[7:0]off;reg[15:0]seen=0;
 initial begin
  for(integer k=0;k<16000;k++)begin
   @(negedge clk);code=4'(k);seen[code]=1;
   for(integer b=0;b<8;b++)begin
    rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);sector[32*b+:32]=(k<16)?0:((k<32)?32'hffffffff:rng);
    rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);held[32*b+:32]=(k<16)?32'hffffffff:((k<32)?0:rng);
   end
   @(posedge clk);#1;off=8'(144*code);v={256'd0,sector};checks++;
   if(one!==144'(v>>off))errors++;v={sector,held};checks++;if(two!==144'(v>>off))errors++;
  end
  $display("TAG_EXTRACT_RESULT checks=%0d codes=%h errors=%0d",checks,seen,errors);
  if(checks!=32000||seen!=16'hffff||errors)$fatal(1,"actual offset extraction failure");$finish;
 end
endmodule
