`timescale 1ns/1ps
module tb_hbm_sm_service_mux #(parameter NCLIENT=4);
import ot_hbm_r14_pkg::*;
reg clk=0;always #5 clk=~clk;reg rst_n=0;
reg[NCLIENT-1:0]c_req_v=0,c_req_we=0,c_rsp_r=0;wire[NCLIENT-1:0]c_req_r,c_rsp_v,c_rsp_we,c_rsp_error;
reg[NCLIENT*37-1:0]c_req_addr=0;reg[NCLIENT*256-1:0]c_req_data=0;reg[NCLIENT*16-1:0]c_req_tag=0;reg[NCLIENT*94-1:0]c_req_context=0;
wire[NCLIENT*256-1:0]c_rsp_data;wire[NCLIENT*16-1:0]c_rsp_tag;wire[NCLIENT*192-1:0]c_rsp_identity;wire[NCLIENT*94-1:0]c_rsp_context;wire[93:0]issuer_req_context;wire[NCLIENT-1:0]c_rsp_identity_checked,c_rsp_context_checked;
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
 always @*begin
  owner_identity='0;owner_identity.die=0;owner_identity.stack=issuer_req_addr[36:35];
  owner_identity.sector={4'b0,issuer_req_addr[34:5]};owner_identity.caller=issuer_req_tag;
  // Test issuer allocation; production caller must supply actual issued namespace.
  owner_identity.client=loader_client;owner_identity.producer=64'hfeed1234;
  owner_identity.transport={16'hb00c,issuer_req_tag};owner_identity.irs_slot=5'd9;owner_identity.irs_serial=32'habc;
 end

ot_hbm_sm_shared_service_join #(.ENABLE(1),.NCLIENT(NCLIENT)) dut(.*);
request_t captured;owned_t returned;integer i,j,k,which=0;reg[93:0]context_saved;reg[255:0]payload;
task tick;begin @(posedge clk);#1;@(negedge clk);#1;end endtask
task failed;begin tick;if(!fault||c_rsp_v!=0||issuer_req_valid)$fatal(1,"fault escaped");$display("PASS rejected %0d",which);$finish;end endtask
initial begin
if($value$plusargs("CASE=%d",which))begin end
repeat(2)tick;rst_n=1;tick;
for(i=0;i<32;i=i+1)begin
 j=i%NCLIENT;k=i%4;context_saved=94'h123456789abcdef+94'(i);payload=256'hfeed0000+256'(i);
 c_req_addr[j*37+:37]={2'(k),35'h40000}+37'(i*32);c_req_we[j]=(i%2);c_req_data[j*256+:256]=payload;c_req_tag[j*16+:16]=16'(i+7);c_req_context[j*94+:94]=context_saved;c_req_v[j]=1;
 #1;while(!c_req_r[j])tick;tick;c_req_v=0;
 while(!issuer_req_valid)tick;
 if(issuer_req_context!=context_saved)$fatal(1,"issuer context lost");
 if(which==1)begin force dut.mux.qn=0;failed;end
 captured=stack_req[k*455+:455];
 if(!stack_req_v[k]||captured.id!=owner_identity)$fatal(1,"actual request identity");
 repeat(2)tick;stack_req_r[k]=1;tick;stack_req_r=0;repeat(3)tick;
 returned='0;returned.id=captured.id;returned.data=payload;returned.physical_tag=12'(i+32);
 if(which==2)returned.id.producer=returned.id.producer^64'b1;
 owned[k*465+:465]=returned;owned_we[k]=captured.we;owned_v[k]=1;
 if(which==2)failed;
 #1;while(!owned_r[k])tick;tick;owned_v=0;
 if(!c_rsp_identity_checked[j]||!c_rsp_context_checked[j]||!c_rsp_v[j]||c_rsp_identity[j*192+:192]!=captured.id||c_rsp_context[j*94+:94]!=context_saved||c_rsp_data[j*256+:256]!=payload||c_rsp_tag[j*16+:16]!=16'(i+7)||c_rsp_we[j]!=captured.we)$fatal(1,"return association");
 if(which==3)begin force dut.mux.rn=0;failed;end
 repeat(2)tick;
 if(!credit_v[k]||credit_id[k*192+:192]!=captured.id)$fatal(1,"reverse real identity");
 credit_r[k]=1;tick;credit_r=0;owned_credit[k]=1;owned_v[k]=1;
 #1;while(!owned_r[k])tick;tick;owned_v=0;owned_credit=0;owned_we=0;
 c_rsp_r[j]=1;tick;c_rsp_r=0;
 if(fault)$fatal(1,"normal fault");
end
$display("PASS 32 transactions four clients actual owned identity and reverse grant");$finish;
end
endmodule
