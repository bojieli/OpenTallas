`timescale 1ns/1ps
module tb_hcoll_landing545;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rn=0,push=0,pop=0;reg[544:0]data;reg[7:0]pe=0;
 wire valid,fault;wire[544:0]head;wire[7:0]epoch;
 reg[544:0]gold[0:299];integer checked=0;
 ot_hcoll_landing545 #(.MUT(MUT))dut(.clk(clk),.rst_n(rn),.push(push),.data(data),.pop(pop),.pop_epoch(pe),.valid(valid),.head(head),.head_epoch(epoch),.fault(fault));
 task automatic retire_head(input integer k);
  begin
   wait(valid&&epoch==8'(k));@(negedge clk);
   if(head!==gold[k])$fatal(1,"LANDING FAIL full545 k=%0d epoch=%0d",k,epoch);
   // Send a deliberately stale pop first. It must leave the same head present.
   pe=8'(k-1);pop=1;@(negedge clk);pop=0;repeat(3)@(negedge clk);
   if(epoch!==8'(k)||!valid||head!==gold[k])$fatal(1,"LANDING FAIL stale epoch k=%0d",k);
   pe=8'(k);pop=1;@(negedge clk);pop=0;repeat(3)@(negedge clk);checked=checked+1;
  end
 endtask
 initial begin
  for(integer k=0;k<300;k=k+1)for(integer b=0;b<545;b=b+1)gold[k][b]=((k*13+b*29)^(k>>2)^(b>>4))&1;
  repeat(8)@(negedge clk);rn=1;repeat(8)@(negedge clk);
  // Full8entries, pointer wrap, head epoch wrap, all545bits and stale command.
  for(integer base_=0;base_<300;base_=base_+8)begin
   for(integer j=base_;j<base_+8&&j<300;j=j+1)begin push=1;data=gold[j];@(negedge clk);end
   push=0;repeat(3)@(negedge clk);
   for(integer j=base_;j<base_+8&&j<300;j=j+1)retire_head(j);
  end
  if(fault||checked!=300)$fatal(1,"LANDING FAIL count/fault");
  $display("LANDING PASS full545 checked=%0d",checked);$finish;
 end
 initial begin #1000000;$fatal(1,"LANDING FAIL timeout");end
endmodule
