// One existing shared-service client, four locally captured native requesters.
module ot_hbm_sm_shared_service_join #(parameter ENABLE=0,LOCAL_DIE=0,RANK_LIMIT=96,NCLIENT=4)(
 input wire clk,rst_n,
 input wire[NCLIENT-1:0]c_req_v,output wire[NCLIENT-1:0]c_req_r,input wire[NCLIENT-1:0]c_req_we,
 input wire[NCLIENT*37-1:0]c_req_addr,input wire[NCLIENT*256-1:0]c_req_data,input wire[NCLIENT*16-1:0]c_req_tag,input wire[NCLIENT*94-1:0]c_req_context,
 output wire[NCLIENT-1:0]c_rsp_v,input wire[NCLIENT-1:0]c_rsp_r,output wire[NCLIENT-1:0]c_rsp_we,c_rsp_error,c_rsp_identity_checked,c_rsp_context_checked,
 output wire[NCLIENT*256-1:0]c_rsp_data,output wire[NCLIENT*16-1:0]c_rsp_tag,output wire[NCLIENT*192-1:0]c_rsp_identity,output wire[NCLIENT*94-1:0]c_rsp_context,
 output wire issuer_req_valid,output wire[36:0]issuer_req_addr,output wire[15:0]issuer_req_tag,output wire[93:0]issuer_req_context,
 input wire hardware_owner_valid,input ot_hbm_r14_pkg::identity_t owner_identity,
 input wire[5:0] loader_client,input wire[6:0] global_rank,
 output wire[3:0] stack_req_v,input wire[3:0] stack_req_r,output wire[1819:0] stack_req,
 input wire[3:0] owned_v,output wire[3:0] owned_r,input wire[1859:0] owned,
 input wire[3:0] owned_we,owned_credit,service_fault,
 output wire[3:0] other_owned_v,input wire[3:0] other_owned_r,
 output wire[1859:0] other_owned,output wire[3:0] other_owned_we,other_owned_credit,
 output wire[3:0] credit_v,input wire[3:0] credit_r,output wire[3:0] credit_we,
 output wire[767:0] credit_id,output wire[47:0] credit_tag,output wire[19:0] credit_beat,
 input wire[3:0] other_credit_v,other_credit_we,output wire[3:0] other_credit_r,
 input wire[767:0] other_credit_id,input wire[47:0] other_credit_tag,input wire[19:0] other_credit_beat,
 output wire busy,output wire[6:0] held_global_rank,output wire fault
);
 wire req_v,req_r,req_we,rsp_v,rsp_r,rsp_we;
 wire[36:0]req_addr;wire[255:0]req_data,rsp_data;wire[15:0]req_tag,rsp_tag;
 wire[31:0]req_strb={32{req_we}};wire[191:0]rsp_identity;
 wire mux_fault,join_fault;
 assign issuer_req_valid=req_v;assign issuer_req_addr=req_addr;assign issuer_req_tag=req_tag;
 assign fault=mux_fault||join_fault;
 ot_hbm_sm_service_mux #(.ENABLE(ENABLE),.NCLIENT(NCLIENT)) mux(.service_fault(join_fault),.fault(mux_fault),.issuer_context(issuer_req_context),.*);
 ot_hbm_sm_loader_identity_join #(.ENABLE(ENABLE),.LOCAL_DIE(LOCAL_DIE),.RANK_LIMIT(RANK_LIMIT)) service(.fault(join_fault),.*);
endmodule
