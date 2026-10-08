// Actual native clients + ONE sharedservice join; fifth client is checked SU reads.
// Generated installedsource constants; installation/liveissuer/PHY remain real external contracts.
module ot_hbm_sm_native_production #(parameter ENABLE=0,PROTECT=0,DESC_HOPS=32,LOCAL_DIE=0,RANK_LIMIT=96)(
 input wire clk,rst_n,installed,run_valid,output wire run_ready,
 input wire[72:0]run_owner,input wire[4:0]run_source,input wire[15:0]issuer_tag,
 input wire[93:0]issuer_grant_context,
 output wire done,input wire done_ready,input wire release_in,output wire released,native_busy,
 output wire su_publication_valid,input wire su_publication_ready,output wire[93:0]su_publication_context,
 input wire su_release_valid,output wire su_release_ready,input wire[93:0]su_release_context,
 input wire su_req_v,output wire su_req_r,input wire su_req_we,input wire[36:0]su_req_addr,
 input wire[255:0]su_req_data,input wire[15:0]su_req_tag,input wire[93:0]su_req_context,
 output wire su_rsp_v,input wire su_rsp_r,output wire su_rsp_we,su_rsp_error,
 output wire[255:0]su_rsp_data,output wire[15:0]su_rsp_tag,output wire[191:0]su_rsp_identity,
 output wire[93:0]su_rsp_context,output wire su_rsp_identity_checked,su_rsp_context_checked,
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
 output wire service_busy,output wire[6:0] held_global_rank,output wire fault
);
 wire[4:0]c_req_v,c_req_r,c_req_we,c_rsp_v,c_rsp_r,c_rsp_we,c_rsp_error,c_rsp_identity_checked,c_rsp_context_checked;
 wire[184:0]c_req_addr;wire[1279:0]c_req_data,c_rsp_data;wire[79:0]c_req_tag,c_rsp_tag;
 wire[469:0]c_req_context,c_rsp_context;wire[959:0]c_rsp_identity;
 wire native_fault,shared_fault;
 wire issuer_mismatch=issuer_req_valid&&hardware_owner_valid&&issuer_grant_context!=issuer_req_context;
 wire association_fault=|(c_rsp_v[3:0]&~(c_rsp_identity_checked[3:0]&c_rsp_context_checked[3:0]));
 wire abort_native=shared_fault||issuer_mismatch||association_fault;
 assign fault=native_fault||abort_native;
 assign c_req_v[4]=su_req_v;assign su_req_r=c_req_r[4];assign c_req_we[4]=su_req_we;
 assign c_req_addr[148+:37]=su_req_addr;assign c_req_data[1024+:256]=su_req_data;assign c_req_tag[64+:16]=su_req_tag;assign c_req_context[376+:94]=su_req_context;
 assign su_rsp_v=c_rsp_v[4];assign c_rsp_r[4]=su_rsp_r;assign su_rsp_we=c_rsp_we[4];assign su_rsp_error=c_rsp_error[4];
 assign su_rsp_data=c_rsp_data[1024+:256];assign su_rsp_tag=c_rsp_tag[64+:16];assign su_rsp_identity=c_rsp_identity[768+:192];assign su_rsp_context=c_rsp_context[376+:94];
 assign su_rsp_identity_checked=c_rsp_identity_checked[4];assign su_rsp_context_checked=c_rsp_context_checked[4];
 ot_hbm_sm_native_clients #(.ENABLE(ENABLE),.PROTECT(PROTECT),.DESC_HOPS(DESC_HOPS)) clients(
 .clk(clk),.rst_n(rst_n),.installed(installed),.run_valid(run_valid),.run_ready(run_ready),.run_owner(run_owner),.run_source(run_source),.issuer_tag(issuer_tag),
 .program_base(32'd119160832),.program_limit(33'd119161352),.program_storage_limit(33'd119161376),.record_count(16'd13),
 .su_publication_valid(su_publication_valid),.su_publication_ready(su_publication_ready),.su_publication_context(su_publication_context),
 .su_release_valid(su_release_valid),.su_release_ready(su_release_ready),.su_release_context(su_release_context),
 .done(done),.done_ready(done_ready),.fault(native_fault),.release_in(release_in),.released(released),.busy(native_busy),
 .c_req_v(c_req_v[3:0]),.c_req_r(c_req_r[3:0]),.c_req_we(c_req_we[3:0]),.c_req_addr(c_req_addr[147:0]),.c_req_data(c_req_data[1023:0]),.c_req_tag(c_req_tag[63:0]),.c_req_context(c_req_context[375:0]),
 .c_rsp_v(c_rsp_v[3:0]),.c_rsp_r(c_rsp_r[3:0]),.c_rsp_we(c_rsp_we[3:0]),.c_rsp_error(c_rsp_error[3:0]),.c_rsp_data(c_rsp_data[1023:0]),.c_rsp_tag(c_rsp_tag[63:0]),.service_fault(abort_native));
 ot_hbm_sm_shared_service_join #(.ENABLE(ENABLE),.LOCAL_DIE(LOCAL_DIE),.RANK_LIMIT(RANK_LIMIT),.NCLIENT(5)) service(
 .hardware_owner_valid(hardware_owner_valid&&!issuer_mismatch),.busy(service_busy),.fault(shared_fault),.*);
endmodule
