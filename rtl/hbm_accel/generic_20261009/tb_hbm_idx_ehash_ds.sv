`timescale 1ns/1ps
import ot_hdc_engram_tables_shipped_pkg::*;
module tb_hbm_idx_ehash_ds;
 parameter integer MUTANT=0;
 reg clk=0;always #416.6665 clk=~clk;
 reg rst_n=0,token_begin=0,accept_valid=0,cmd_valid=0,cmd_first=0,row_ready=1;
 reg [2:0] accept_slot=0,cmd_op=4,cmd_layer=0,cmd_slot=0;
 reg [16:0] cmd_cid=0;
 reg [255:0] b_mult;
 reg [767:0] b_prime,b_offset;
 wire cmd_ready,row_valid,done,fault;wire[31:0]row_id;wire[4:0]row_column;
 ot_hbm_idx_ehash_ds #(.ENABLE_GENERIC(1),.MUTANT(MUTANT))dut(.*);
 reg[16:0]hist[0:2];reg[16:0]snap[0:7][0:2];reg[16:0]win[0:7][0:3];
 reg[7:0]seen=0;integer cases=0,beats=0,cycle=0; always @(posedge clk)cycle=cycle+1;
 task automatic begin_token;
  @(negedge clk);token_begin=1;@(negedge clk);token_begin=0;seen=0;
 endtask
 task automatic send(input integer slot,l,cid,first);
  reg[63:0]roll,product,mult;reg[31:0]prime,offs,expected;integer col,s,h,c,ticks,start_cycle;
  begin
   if(!seen[slot])begin
    win[slot][0]=cid;
    for(s=1;s<4;s=s+1)win[slot][s]=first?2:hist[s-1];
    for(s=0;s<3;s=s+1)begin hist[s]=win[slot][s];snap[slot][s]=hist[s];end
    seen[slot]=1;
   end
   @(negedge clk);cmd_slot=slot;cmd_layer=l;cmd_cid=cid;cmd_first=first;
   for(s=0;s<4;s=s+1)b_mult[64*s+:64]=ENG_NIB[64*((l*4+s)*64+1)+:64];
   for(c=0;c<24;c=c+1)begin b_prime[32*c+:32]=ENG_PRIME[24*(l*24+c)+:24];b_offset[32*c+:32]=ENG_OFFSET[29*(l*24+c)+:29];end
   while(!cmd_ready)@(negedge clk);
   cmd_valid=1;start_cycle=cycle;@(negedge clk);cmd_valid=0;ticks=0;
   for(col=0;col<24;col=col+1)begin
    while(!row_valid)begin @(negedge clk);ticks=ticks+1;if(ticks>100)$fatal(1,"timeout");if(fault)$fatal(1,"unexpected fault");end
    roll=0;
    for(s=0;s<col/8+2;s=s+1)begin mult=ENG_NIB[64*((l*4+s)*64+1)+:64];product=win[slot][s]*mult;roll=roll^product;end
    prime=ENG_PRIME[24*(l*24+col)+:24];offs=ENG_OFFSET[29*(l*24+col)+:29];expected=(roll%prime)+offs;
    if(row_column!=col||row_id!=expected)$fatal(1,"EHASH mismatch case=%0d col=%0d got=%0d ref=%0d",cases,col,row_id,expected);
    beats=beats+1;@(negedge clk);
   end
   while(!cmd_ready)@(negedge clk);$display("EHASH_CYCLES layer=%0d slot=%0d command_to_ready=%0d first_row_wait=%0d",l,slot,cycle-start_cycle,ticks);cases=cases+1;
  end
 endtask
 initial begin
  for(integer s=0;s<3;s=s+1)hist[s]=2;
  repeat(3)@(negedge clk);rst_n=1;
  begin_token();send(0,0,311,1);send(0,1,311,1);send(1,1,99091,0);send(1,0,99091,0);send(2,0,1741,0);send(2,1,1741,0);
  @(negedge clk);accept_slot=1;accept_valid=1;
  @(negedge clk);accept_valid=0;for(integer s=0;s<3;s=s+1)hist[s]=snap[1][s];seen=0;
  send(0,0,779,0);send(0,1,779,0);
  begin_token();send(0,1,412,0);send(0,0,412,0);
  // A changed dynamic B must fail closed; mutant 4 ignores this requirement.
  @(negedge clk);cmd_layer=0;cmd_slot=0;cmd_cid=412;b_mult[63:0]=b_mult[63:0]^1;cmd_valid=1;
  @(negedge clk);cmd_valid=0;@(negedge clk);
  if(!fault)$fatal(1,"EHASH B mismatch was not rejected");
  $display("PASS EHASH DS LOCKSTEP HISTORY ACCEPT %0d cases %0d row ids",cases,beats);$finish;
 end
endmodule
