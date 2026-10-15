`timescale 1ns/1ps
module tb_s81_engram_dispatch #(parameter MUT=0);
 reg clk=0;always #1 clk=~clk;reg rst=0;reg [84:0] cmd=0;reg [8:0] ld=0,md=0;
 wire [84:0] lc,mc;wire [8:0] done;wire [1:0] st;
 ot_s81_engram_dispatch #(.MUT(MUT)) dut(clk,rst,cmd,done,st,lc,mc,ld,md,2'b10,2'b10);
 integer cyc=0,lkc=0,mkc=0,returned=0,lexpect=0,mexpect=64,lp=-1,mp=-1,i;reg [19:0] seen=0;reg overflow_mode=0;
 always @(posedge clk)begin
  cyc=cyc+1;
  if(lc[84])begin if(lc[30]||lc[6:0]>=10)$fatal(1,"wrong lookup command");lkc=lkc+1;end
  if(mc[84])begin if(mc[30]||mc[6:0]<64||mc[6:0]>=74)$fatal(1,"wrong MIX selector/tag");mkc=mkc+1;end
  if(done[8]&&!overflow_mode)begin
   if(done[7:0]<10)begin
    if(done[7:0]!=lexpect)$fatal(1,"lookup tag/order mismatch");lexpect=lexpect+1;
    if(seen[done[7:0]])$fatal(1,"duplicate lookup completion");seen[done[7:0]]=1;
    if(lp<0)lp=cyc%2;else if(lp!=cyc%2)$fatal(1,"lookup service phase changed");
   end else if(done[7:0]>=64&&done[7:0]<74)begin
    if(done[7:0]!=mexpect)$fatal(1,"MIX tag/order mismatch");mexpect=mexpect+1;
    if(seen[10+done[7:0]-64])$fatal(1,"duplicate MIX completion");seen[10+done[7:0]-64]=1;
    if(mp<0)mp=cyc%2;else if(mp!=cyc%2)$fatal(1,"MIX service phase changed");
   end else $fatal(1,"unexpected completion tag");
   returned=returned+1;
  end
  if(st[0]&&!overflow_mode)$fatal(1,"unexpected dispatcher fault");
  if(cyc>600)$fatal(1,"timeout");
 end
 initial begin
  repeat(5)@(negedge clk);rst=1;wait(st[1]);
  // Twenty descriptors cross both destinations; ten per lane wraps each ring.
  for(i=0;i<20;i=i+1)begin
   @(negedge clk);cmd=0;cmd[84]=1;cmd[6:0]=(i%2)?64+i/2:i/2;cmd[30]=i%2;
  end
  @(negedge clk);cmd=0;
  // Deliberate simultaneous endpoint completions and idle gaps exercise the
  // fixed, non-skipping calendar. Pairs spaced two cycles cannot overflow.
  for(i=0;i<10;i=i+1)begin
   repeat((i%3==0)?5:1)@(negedge clk);ld={1'b1,8'(i)};md={1'b1,8'(64+i)};
   @(negedge clk);ld=0;md=0;
  end
  wait(returned==20);repeat(12)@(negedge clk);
  if(seen!=20'hfffff||lkc!=10||mkc!=10||lp==mp)$fatal(1,"accounting/phase failure");
  // More completions than the reservation bound is a fault, never a stall.
  overflow_mode=1;
  for(i=0;i<24;i=i+1)begin @(negedge clk);ld={1'b1,8'(i)};md={1'b1,8'(64+i)};end
  @(negedge clk);ld=0;md=0;repeat(12)@(negedge clk);
  if(!st[0])$fatal(1,"completion overflow not detected");
  $display("PASS dispatcher20 tags exact, selector stripped, fixed alternating service, ring wrap and overflow fault");$finish;
 end
endmodule
