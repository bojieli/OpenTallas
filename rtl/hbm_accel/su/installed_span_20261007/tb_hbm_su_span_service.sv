`timescale 1ns/1ps
module tb_hbm_su_span_service;
localparam NCLIENT=5;
import ot_hbm_r14_pkg::*;
reg clk=0;always #5 clk=~clk;reg rst_n=0;
wire[NCLIENT-1:0]c_req_v,c_req_we,c_rsp_r;wire[NCLIENT-1:0]c_req_r,c_rsp_v,c_rsp_we,c_rsp_error;
wire[NCLIENT*37-1:0]c_req_addr;wire[NCLIENT*256-1:0]c_req_data;wire[NCLIENT*16-1:0]c_req_tag;wire[NCLIENT*94-1:0]c_req_context;
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

assign c_req_v[3:0]=0;assign c_req_we[3:0]=0;assign c_rsp_r[3:0]=0;
assign c_req_addr[147:0]=0;assign c_req_data[1023:0]=0;assign c_req_tag[63:0]=0;assign c_req_context[375:0]=0;
reg bind_v=0,publication_v=0,read_v=0,result_r=0,release_v=0;
wire bind_r,publication_r,read_r,result_v,release_r,retained,span_fault;
reg [23:0]read_word=123;reg [12:0]read_consumer=0;
wire [31:0]result_data;wire [12:0]result_consumer;
localparam [72:0] OWNER=73'h123456789abcdef;
ot_hbm_su_installed_span_client #(.ENABLE(1)) consumer(
 .clk(clk),.por_n(rst_n),.warm_reset(1'b0),.transport_fault(fault),
 .bind_v(bind_v),.bind_r(bind_r),.installed_checked(2'b11),.bind_owner(OWNER),.bind_record(16'd0),.bind_tag(16'd7),.bind_source(5'd2),
 .logical_base(24'd123),.rows(13'd1),.byte_base(37'd119440480),.byte_limit(37'd119440512),
 .publication_v(publication_v),.publication_r(publication_r),.publication_owner(OWNER),.publication_record(16'd0),.publication_source(5'd2),
 .read_v(read_v),.read_r(read_r),.read_word(read_word),.read_consumer(read_consumer),
 .c_req_v(c_req_v[4]),.c_req_r(c_req_r[4]),.c_req_we(c_req_we[4]),.c_req_addr(c_req_addr[148+:37]),
 .c_req_data(c_req_data[1024+:256]),.c_req_tag(c_req_tag[64+:16]),.c_req_context(c_req_context[376+:94]),
 .c_rsp_v(c_rsp_v[4]),.c_rsp_r(c_rsp_r[4]),.c_rsp_we(c_rsp_we[4]),.c_rsp_error(c_rsp_error[4]),
 .c_rsp_identity_checked(c_rsp_identity_checked[4]),.c_rsp_context_checked(c_rsp_context_checked[4]),
 .c_rsp_data(c_rsp_data[1024+:256]),.c_rsp_tag(c_rsp_tag[64+:16]),.c_rsp_context(c_rsp_context[376+:94]),
 .result_v(result_v),.result_r(result_r),.result_data(result_data),.result_consumer(result_consumer),
 .release_v(release_v),.release_r(release_r),.release_owner(OWNER),.release_record(16'd0),.release_source(5'd2),.retained(retained),.fault(span_fault));
request_t captured;owned_t returned;integer i,j,which=0;reg[255:0]payload;
task tick;begin @(posedge clk);#1;@(negedge clk);#1;end endtask
initial begin
if($value$plusargs("CASE=%d",which))begin end
repeat(2)tick;rst_n=1;tick;bind_v=1;#1;if(!bind_r)$fatal(1,"bind");tick;bind_v=0;
publication_v=1;#1;if(!publication_r)$fatal(1,"publication");tick;publication_v=0;
for(i=0;i<8;i=i+1)begin
 read_word=123+i;read_consumer=13'(i+17);read_v=1;#1;if(!read_r)$fatal(1,"read not admitted");tick;read_v=0;
 while(!issuer_req_valid)tick;
 if(issuer_req_context!={OWNER,16'd0,5'd2}||issuer_req_addr!=37'd119440480)$fatal(1,"actual installed context/address lost");
 captured=stack_req[0+:455];
 if(!stack_req_v[0]||captured.id!=owner_identity)$fatal(1,"actual request identity");
 repeat(2)tick;stack_req_r[0]=1;tick;stack_req_r=0;repeat(3)tick;
 for(j=0;j<8;j=j+1)payload[j*32+:32]=32'h3f800000+j;
 returned='0;returned.id=captured.id;returned.data=payload;returned.physical_tag=12'(i+32);
 if(which==1)returned.id.producer=returned.id.producer^64'b1;
 owned[0+:465]=returned;owned_we[0]=captured.we;owned_v[0]=1;
 if(which==1)begin repeat(3)tick;if(!fault||!span_fault||result_v)$fatal(1,"wrong owned producer escaped");$display("PASS SPAN_SERVICE rejected wrong owned producer");$finish;end
 #1;while(!owned_r[0])tick;tick;owned_v=0;
 if(which==2)begin force dut.mux.rn=0;repeat(2)tick;if(!fault||!span_fault||result_v)$fatal(1,"response bank fault escaped");$display("PASS SPAN_SERVICE rejected response bank corruption");$finish;end
 while(!result_v)tick;
 if(result_data!=32'h3f800000+i||result_consumer!=i+17||span_fault)$fatal(1,"actual checked operand read");
 repeat(2)tick;
 if(!credit_v[0]||credit_id[0+:192]!=captured.id)$fatal(1,"reverse real identity");
 credit_r[0]=1;tick;credit_r=0;owned_credit[0]=1;owned_v[0]=1;
 #1;while(!owned_r[0])tick;tick;owned_v=0;owned_credit=0;
 result_r=1;tick;result_r=0;
 if(fault||span_fault)$fatal(1,"normal fault");
end
release_v=1;#1;if(!release_r)$fatal(1,"allocation release");tick;release_v=0;
if(retained||fault||span_fault)$fatal(1,"release debt");
$display("PASS SPAN_SERVICE 8 exact operands installed record0 actual shared identity/reverse grant");$finish;
end
endmodule
