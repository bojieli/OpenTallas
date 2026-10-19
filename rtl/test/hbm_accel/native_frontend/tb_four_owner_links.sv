`timescale 1ns/1ps
module tb_four_owner_links;
 parameter integer MUT=0;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0;reg[3:0] iv=0,it=0;reg[7:0] permit=8'hff;
 reg[1139:0] ip=0;wire[3:0] ov,ot,fault;wire[1139:0] op;
 ot_hbm_svc_four_owner_links #(.MUT(MUT)) dut(.clk({4{clk}}),.rst_n(rst_n),
  .in_v(iv),.in_packet(ip),.in_target(it),.target_reserved(permit),
  .out_v(ov),.out_packet(op),.out_target(ot),.fault(fault));
 integer checks=0,cycle,j,k,phase;reg[3:0] prev_v=0,prev_t=0,prev_v2=0,prev_t2=0;
 reg[1139:0] prev_p=0,prev_p2=0;reg[10:0] ordinal;
 task automatic fail(input string s);begin $display("FAIL %s cycle=%0d",s,cycle);$fatal(1);end endtask
 task automatic tick(input bit verify);begin
  @(posedge clk);#0.01;
  if(verify)begin
   if(ov!==prev_v2)fail("valid age/reset");
   for(integer q=0;q<4;q=q+1)if(ov[q])begin
    if(op[285*q+:285]!==prev_p2[285*q+:285])fail("packet identity/epoch/data");
    if(ot[q]!==prev_t2[q])fail("target association");
    checks=checks+1;
   end
   if(fault!==0)fail("unexpected fault");
  end
  prev_v2=prev_v;prev_p2=prev_p;prev_t2=prev_t;prev_v=iv;prev_p=ip;prev_t=it;
 end endtask
 task automatic reset_all;begin
  @(negedge clk);rst_n=0;iv=0;prev_v=0;prev_v2=0;
  #0.1;if(ov!==0)fail("asynchronous occupied cancellation");
  repeat(3)@(posedge clk);
  @(negedge clk);rst_n=1;
  repeat(3)begin @(posedge clk);#0.01;if(ov!==0)fail("startup stale valid");end
  prev_v=0;prev_v2=0;
 end endtask
 initial begin
  for(phase=0;phase<8;phase=phase+1)begin
   reset_all();
   for(cycle=0;cycle<1024;cycle=cycle+1)begin
    @(negedge clk);iv=(cycle%11==0)?0:4'hf;permit=8'hff;
    for(j=0;j<4;j=j+1)begin
     ordinal=11'((cycle*4+j)&2047);it[j]=ordinal[2];
     ip[285*j+:285]={ordinal,2'(cycle%4),16'(cycle+phase*1024),
       32'(cycle),32'(j),32'(phase),32'hdeadcafe,32'(cycle^j),32'h76543210,32'hfedcba98,32'(cycle+17)};
    end
    tick(1);
   end
   // Reset at eight offsets while all four rings contain live packets.
   @(negedge clk);#(0.02*phase);rst_n=0;#0.01;
   if(ov!==0)fail("occupied reset leaked valid");
  end
  for(k=1;k<=3;k=k+1)begin
   reset_all();@(negedge clk);iv=1;permit=8'hff;ip=0;it=0;
   if(k==1)ip[274]=1; // wrong low-two owner identity
   if(k==2)it[0]=1;  // wrong explicit target vs ordinal[2]
   if(k==3)permit[0]=0; // reservation withdrawn for occupied payload
   tick(0);@(negedge clk);iv=0;tick(0);@(negedge clk);tick(0);
   if(ov!==0)fail("malformed packet escaped");
   if(!fault[0])fail("missing malformed fault");
   repeat(4)begin @(negedge clk);tick(0);if(ov!==0)fail("fault not sticky");end
  end
  $display("PASS four_owner_links checks=%0d rings=4 slots=4 resets=8 malformed=3 edges=3",checks);$finish;
 end
endmodule
