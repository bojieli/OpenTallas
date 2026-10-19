`timescale 1ns/1ps
module tb_owner_issue;
 parameter integer MUT=0;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0,iv=0,kr=1,stop=0;reg[50:0] req=0;wire ir,kv,fault;wire[50:0] out_req;wire[2:0] occupancy;
 ot_hbm_owner_issue_native #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.in_v(iv),.in_request(req),.in_ready(ir),
  .k_ready(kr),.k_v(kv),.k_request(out_req),.stop(stop),.fault(fault),.occupancy(occupancy));
 reg[50:0] fifo[$];reg[50:0] expected;integer sent,received,cycle,phase,checks=0;reg last_kv=0;
 function automatic [50:0] packet(input integer n,input integer p);packet={17'(n+4096*p),4'((n%5==0)?1:4),30'(n*32+128*p)};endfunction
 task automatic fail(input string s);begin $display("FAIL owner_issue %s phase=%0d cycle=%0d sent=%0d received=%0d",s,phase,cycle,sent,received);$fatal(1);end endtask
 task automatic reset_all;begin
  @(negedge clk);rst_n=0;iv=0;stop=0;fifo.delete();sent=0;received=0;last_kv=0;
  #0.02;if(ir||kv||fault||occupancy)fail("asynchronous occupied reset");
  repeat(3)@(posedge clk);@(negedge clk);rst_n=1;repeat(3)@(posedge clk);
 end endtask
 task automatic step(input integer target);begin
  @(negedge clk);iv=(sent<target);req=packet(sent,phase);
  kr=(phase==0)?1:(cycle<20)?0:((cycle%7!=2)&&(cycle%11!=4));
  @(posedge clk);
  if(iv&&ir)begin fifo.push_back(req);sent=sent+1;end
  if(kv&&last_kv)fail("missing confirmation bubble");last_kv=kv;
  if(kv&&kr)begin
   if(fifo.size()==0)fail("duplicate or unreserved receiver event");expected=fifo.pop_front();
   if(out_req!==expected)fail("tag/address/length identity");received=received+1;checks=checks+1;
  end
  #0.01;if(fault||occupancy>4)fail("finite capacity over-admission");
 end endtask
 initial begin
  for(phase=0;phase<2;phase=phase+1)begin
   reset_all();cycle=0;
   while(received<1000&&cycle<10000)begin step(1000);cycle=cycle+1;end
   if(received!=1000||sent!=1000||fifo.size()!=0)fail("finite drain");
   if(phase==0&&cycle>2010)fail("II2 production command budget");
   $display("ISSUE_RATE phase=%0d cycles=%0d accepted=%0d",phase,cycle,received);
  end
  for(phase=2;phase<10;phase=phase+1)begin
   reset_all();for(cycle=0;cycle<8;cycle=cycle+1)step(100);
   @(negedge clk);#(0.02*(phase-2));rst_n=0;#0.01;if(ir||kv||fault||occupancy)fail("occupied reset leak");
  end
  $display("PASS owner_issue checks=%0d pending_slots4 native_ready_history confirmationII2 resets8",checks);$finish;
 end
endmodule
