`timescale 1ns/1ps
module tb_mu_embedding_epoch_masks;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,av=0,ps=0,fs=0,cs=0,rs=0,ts=0;
 reg [1:0] au=0,fu=0,cu=0;reg [15:0] ae=0;reg [3:0] pm=0,tm=0;
 wire [15:0] fe,ee,ce;wire fault,bound_fault;
 integer mut=0,m,u,k,checks=0;reg [15:0] expected[0:3];
 qfd_mu_embedding_epoch_publication #(.ENABLE(1)) dut(.ck(ck),.rst_n(rst_n),
 .accepted_v(av),.accepted_user(au),.accepted_epoch(ae),.publish_slot(ps),.publish_mask(pm),
 .fetch_slot(fs),.fetch_user(fu),.consume_slot(cs),.consume_user(cu),.release_slot(rs),
 .retire_slot(ts),.retire_mask(tm),.fetch_epoch(fe),.expected_epoch(ee),.core_epoch(ce),.fault(fault));
 qfd_mu_embedding_epoch_publication #(.ENABLE(1),.NU(3)) bounded(.ck(ck),.rst_n(rst_n),
 .accepted_v(1'b0),.accepted_user(2'b0),.accepted_epoch(16'b0),
 .publish_slot(mut==6&&ps),.publish_mask(4'b1000),.fetch_slot(1'b0),.fetch_user(2'b0),
 .consume_slot(1'b0),.consume_user(2'b0),.release_slot(1'b0),.retire_slot(1'b0),.retire_mask(4'b0),
 .fetch_epoch(),.expected_epoch(),.core_epoch(),.fault(bound_fault));
 task tick;begin @(posedge ck);#0.1;@(negedge ck);end endtask
 task check;begin if(fault||bound_fault)$fatal(1,"MASK_FAIL sticky fault mut=%0d mask=%h",mut,pm);checks=checks+1;end endtask
 initial begin
  void'($value$plusargs("MUT=%d",mut));tick();rst_n=1;tick();
  // Exhaust every nonempty four-bank mask, including all seven legal filler combinations.
  for(m=1;m<16;m=m+1)begin
   for(u=0;u<4;u=u+1)if((m>>u)&1)begin
    av=1;au=2'(u);ae=16'(m*16+u);expected[u]=ae;tick();av=0;
   end
   ps=1;pm=4'(m);if(mut==1&&m==6)pm=4'b0010;
   if(mut==2&&m==1)pm=4'b1001;
   if(mut==5&&m==1)pm=0;
   tick();ps=0;check();
   for(u=0;u<4;u=u+1)if((m>>u)&1)begin
    fu=2'(u);cu=2'(u);#0.1;
    if(fe!==expected[u] || ce!==expected[u])$fatal(1,"MASK_FAIL wrong mask/epoch mask=%h user=%0d",m,u);
    fs=1;tick();fs=0;
    // Accept the next epoch while the previous epoch remains resident and active.
    av=1;au=2'(u);ae=expected[u]+16'd64;tick();av=0;
    if(mut==3)begin ps=1;pm=4'b1<<u;end
    if(mut==4)begin ts=1;tm=4'b1<<u;end
    tick();ps=0;ts=0;check();
    if(ee!==expected[u] || ce!==expected[u])$fatal(1,"MASK_FAIL latest pending substituted");
    cs=1;tick();cs=0;rs=1;tick();rs=0;check();
   end
   // Publish every pending reload together; verify distinct per-bank epochs survive.
   ps=1;pm=4'(m);tick();ps=0;check();
   for(u=0;u<4;u=u+1)if((m>>u)&1)begin
    fu=2'(u);#0.1;if(fe!==expected[u]+16'd64)$fatal(1,"MASK_FAIL reload epoch user=%0d",u);
   end
   ts=1;tm=4'(m);tick();ts=0;check();
   if((dut.active_valid & 4'(m))!=0 || (dut.pending_valid & 4'(m))!=0)$fatal(1,"MASK_FAIL retirement");
  end
  $display("MASK_PASS all15 masks initial+reload publication/retirement checks=%0d",checks);$finish;
 end
endmodule
