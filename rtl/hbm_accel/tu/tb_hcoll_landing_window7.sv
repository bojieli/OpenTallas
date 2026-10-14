`timescale 1ns/1ps
module tb_hcoll_landing_window7;
 reg clk=0;always #5 clk=~clk;reg rn=0,push=0,pop=0,active=0;reg[544:0]data;reg[7:0]pe=0,consume=0;
 wire valid,fault,cv,cf;wire[3814:0]heads,cached;wire[7:0]epoch,ce;wire[3:0]count,cn;
 reg[544:0]gold[0:511];integer checked=0,cycles=0,first=0;
 wire[7:0]offset=consume-ce;
 ot_hcoll_landing545 dut(.clk(clk),.rst_n(rn),.push(push),.data(data),.pop(pop),.pop_epoch(pe),.valid(valid),.heads(heads),.head_count(count),.head_epoch(epoch),.fault(fault));
 ot_hcoll_landing_capture7 snapshot(.clk(clk),.rst_n(rn),.valid(valid),.fault(fault),.heads(heads),.epoch(epoch),.count(count),.out_valid(cv),.out_fault(cf),.out_heads(cached),.out_epoch(ce),.out_count(cn));
 always @(posedge clk)begin
  cycles=cycles+1;
  if(!rn)begin pop<=0;consume<=0;end
  else begin
   pop<=0;
   if(active&&cv&&offset<7&&offset<cn)begin
    if(cached[545*offset+:545]!==gold[checked])$fatal(1,"LANDING_WINDOW FAIL full545 checked=%0d offset=%0d",checked,offset);
    pe<=consume;pop<=1;consume<=consume+1'b1;
    if(checked%8==0)first=cycles;
    checked=checked+1;
    if(checked%8==0)begin
     if(cycles-first!=7)$fatal(1,"LANDING_WINDOW FAIL throughput burst=%0d cycles=%0d",checked/8,cycles-first+1);
     active<=0;
    end
   end
   if(fault||cf)$fatal(1,"LANDING_WINDOW FAIL overflow");
  end
 end
 initial begin
  for(integer k=0;k<512;k=k+1)begin
   for(integer b=0;b<545;b=b+1)gold[k][b]=((k*13+b*29)^(k>>2)^(b>>4))&1;
   gold[k][31:0]=k;
  end
  repeat(8)@(negedge clk);rn=1;repeat(16)@(negedge clk);
  for(integer base_=0;base_<512;base_=base_+8)begin
   for(integer j=base_;j<base_+8;j=j+1)begin push=1;data=gold[j];@(negedge clk);end
   push=0;wait(cv&&ce==8'(base_)&&cn==8);@(negedge clk);active=1;
   wait(checked==base_+8);wait(dut.count==0);@(negedge clk);
  end
  repeat(12)@(negedge clk);
  $display("LANDING_WINDOW PASS full545 checked=%0d full8bursts=64 II=1 cycles=%0d",checked,cycles);$finish;
 end
 initial begin #1000000;$fatal(1,"LANDING_WINDOW FAIL timeout checked=%0d",checked);end
endmodule
