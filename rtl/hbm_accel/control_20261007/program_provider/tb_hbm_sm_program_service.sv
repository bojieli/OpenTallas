`timescale 1ns/1ps
module tb_hbm_sm_program_service;
 import ot_hbm_r14_pkg::*;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,region_valid=1;
 reg[31:0] virtual_base=32'h1000;reg[32:0] virtual_limit=33'h1220;
 reg[36:0] physical_base=37'h1800040000;
 reg[15:0] request_tag=0;
 reg mem_req_valid=0,mem_rsp_ready=0;wire mem_req_ready,mem_rsp_valid,mem_rsp_error;
 reg[31:0] mem_req_addr=32'h1000;wire[31:0] mem_rsp_addr,mem_rsp_data;
 wire issuer_req_valid;wire[36:0] issuer_req_addr;wire[15:0] issuer_req_tag;
 reg hardware_owner_valid=1;identity_t owner_identity;
 reg[5:0] loader_client=6'd17;reg[6:0] global_rank=7'd63;
 wire[3:0] stack_req_v;reg[3:0] stack_req_r=0;wire[1819:0] stack_req;
 reg[3:0] owned_v=0;wire[3:0] owned_r;reg[1859:0] owned=0;
 reg[3:0] owned_we=0,owned_credit=0,service_fault=0;
 wire[3:0] other_owned_v;reg[3:0] other_owned_r=0;
 wire[1859:0] other_owned;wire[3:0] other_owned_we,other_owned_credit;
 wire[3:0] credit_v,credit_we;reg[3:0] credit_r=0;
 wire[767:0] credit_id;wire[47:0] credit_tag;wire[19:0] credit_beat;
 reg[3:0] other_credit_v=0,other_credit_we=0;wire[3:0] other_credit_r;
 reg[767:0] other_credit_id=0;reg[47:0] other_credit_tag=0;reg[19:0] other_credit_beat=0;
 wire busy,fault;wire[6:0] held_global_rank;
 ot_hbm_sm_program_service_join #(.ENABLE(1)) dut(.*);
 always @*begin
  owner_identity='0;owner_identity.die=0;owner_identity.stack=issuer_req_addr[36:35];
  owner_identity.sector={4'b0,issuer_req_addr[34:5]};owner_identity.caller=issuer_req_tag;
  // Test issuer allocation; production caller must supply actual issued namespace.
  owner_identity.client=loader_client;owner_identity.producer=64'hfeed1234;
  owner_identity.transport={16'hb00c,issuer_req_tag};owner_identity.irs_slot=5'd9;owner_identity.irs_serial=32'habc;
 end
 reg[31:0] program_words[0:135];
 request_t captured;owned_t returned;
 integer i,j,k,which=0;
 reg[31:0] original;reg[255:0] payload;
 task tick;begin @(posedge clk);#1;@(negedge clk);#1;end endtask
 task expect_fault;begin
  #1;if(!fault||mem_rsp_valid||issuer_req_valid)$fatal(1,"failure not contained");
  tick;owned_v=0;service_fault=0;mem_req_valid=0;
  repeat(3)tick;
  if(!fault||mem_rsp_valid||issuer_req_valid)$fatal(1,"fault not sticky");
  $display("PASS negative %0d",which);$finish;
 end endtask
 initial begin
  if($value$plusargs("CASE=%d",which))begin end
  for(j=0;j<136;j=j+1)program_words[j]=0;
  $readmemh("results/rtl/hbm_sm_command_20261007/stress_seq.hex",program_words,0,129);
  repeat(2)tick;rst_n=1;tick;
  if(which==1)begin mem_req_addr=32'h1001;mem_req_valid=1;expect_fault;end
  if(which==2)begin mem_req_addr=32'h1220;mem_req_valid=1;expect_fault;end
  if(which==3)begin physical_base=37'h1fffffffE0;virtual_limit=33'h1040;mem_req_valid=1;expect_fault;end
  for(i=0;i<130;i=i+1)begin
   request_tag=16'(i+1);mem_req_addr=32'h1000+32'(4*i);mem_req_valid=1;
   while(!mem_req_ready)tick;
   tick;mem_req_valid=0;
   while(!issuer_req_valid)tick;
   repeat(2)tick;
   if(which==9)begin force dut.words.state=4'b0110;expect_fault;end
   if(which==7)begin original=dut.words.saved_addr;force dut.words.saved_addr=32'h1001;expect_fault;end
   k=int'(issuer_req_addr[36:35]);
   if(k!=3||issuer_req_addr!=physical_base+37'((i/8)*32))$fatal(1,"physical mapping");
   captured=stack_req[k*455+:455];
   if(!stack_req_v[k]||captured.id!=owner_identity||captured.we||captured.len!=1)$fatal(1,"request ownership");
   stack_req_r[k]=1;tick;stack_req_r=0;
   repeat(3)tick;
   returned='0;returned.id=captured.id;returned.physical_tag=12'h412;
   for(j=0;j<8;j=j+1)payload[j*32+:32]=program_words[(i/8)*8+j];
   returned.data=payload;
   if(which==4)returned.id.caller=returned.id.caller^16'h1;
   if(which==10)returned.id.sector=returned.id.sector^34'h1;
   if(which==5)owned_we[k]=1;
   owned[k*465+:465]=returned;owned_v[k]=1;
   if(which==6)service_fault[k]=1;
   if((which>=4&&which<=6)||which==10)begin tick;expect_fault;end
   #1;while(!owned_r[k])tick;
   tick;owned_v=0;
   if(which==8)begin original=dut.words.saved_data^32'h1;force dut.words.saved_data=original;expect_fault;end
   if(!mem_rsp_valid||mem_rsp_addr!=mem_req_addr||mem_rsp_data!=program_words[i]||mem_rsp_error)$fatal(1,"native word mismatch %0d",i);
   repeat(2)tick;
   if(!credit_v[k]||credit_id[k*192+:192]!=captured.id||credit_tag[k*12+:12]!=returned.physical_tag)$fatal(1,"reverse credit");
   credit_r[k]=1;tick;credit_r=0;
   owned_credit[k]=1;owned_v[k]=1;
   #1;while(!owned_r[k])tick;
   tick;owned_v=0;owned_credit=0;
   if(fault||busy)$fatal(1,"join completion");
   mem_rsp_ready=1;tick;mem_rsp_ready=0;
  end
  $display("PASS native_records=13 words=130 real_owned_and_reverse_credit=130");$finish;
 end
 initial begin #1000000;$fatal(1,"bench deadlock");end
endmodule
