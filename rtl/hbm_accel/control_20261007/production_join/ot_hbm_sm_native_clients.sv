// Native full-shape production candidate. Four finite clients share one service.
// Model precedes RTL: tools/hbm_sm_native_production_model.py.
// Program constants are bound by a generated immutable installed-source parent.
module ot_hbm_sm_native_clients #(parameter ENABLE=0,PROTECT=0,DESC_HOPS=32)(
 input wire clk,rst_n,installed,run_valid,output wire run_ready,
 input wire[31:0] program_base,input wire[32:0] program_limit,program_storage_limit,
 input wire[15:0] record_count,issuer_tag,
 input wire[72:0]run_owner,input wire[4:0]run_source,output wire[375:0]c_req_context,
 output wire done,input wire done_ready,output wire fault,
 input wire release_in,output wire released,busy,
 output wire su_publication_valid,input wire su_publication_ready,output wire[93:0]su_publication_context,
 input wire su_release_valid,output wire su_release_ready,input wire[93:0]su_release_context,
 output wire[3:0] c_req_v,input wire[3:0] c_req_r,output wire[3:0] c_req_we,
 output wire[147:0] c_req_addr,output wire[1023:0] c_req_data,output wire[63:0] c_req_tag,
 input wire[3:0] c_rsp_v,output wire[3:0] c_rsp_r,input wire[3:0] c_rsp_we,c_rsp_error,
 input wire[1023:0] c_rsp_data,input wire[63:0] c_rsp_tag,input wire service_fault
);
 (* keep=1,dont_touch=1 *)reg[93:0] context_q,context_n;
 (* keep=1,dont_touch=1 *)reg context_live,context_live_n,context_bad,context_bad_n;
 wire context_fault=context_bad || context_bad==context_bad_n || context_q!=~context_n || context_live==context_live_n || arrive_seen==arrive_seen_n;
 wire native_run_ready;wire native_run_valid=run_valid&&installed&&!context_live&&!context_fault;
 assign run_ready=native_run_ready&&installed&&!context_live&&!context_fault;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin context_q<=0;context_n<=~94'b0;context_live<=0;context_live_n<=1;context_bad<=0;context_bad_n<=1;end
 else begin
 if(context_fault)begin context_bad<=1;context_bad_n<=0;end
 if(run_valid&&run_ready)begin context_q<={issuer_tag,run_owner,run_source};context_n<=~{issuer_tag,run_owner,run_source};context_live<=1;context_live_n<=0;end
 if(done&&done_ready)begin context_live<=0;context_live_n<=1;end
 end end
 wire[15:0]held_issuer_tag=context_q[93:78];
 wire mem_req_valid,mem_req_ready,mem_rsp_valid,mem_rsp_ready,mem_rsp_error;
 wire[31:0]mem_req_addr,mem_rsp_addr,mem_rsp_data;
 wire alloc_valid,alloc_ready,alloc_rsp_valid,alloc_rsp_ready,alloc_rsp_error;
 wire[15:0]alloc_record,alloc_rsp_record;wire[23:0]alloc_lines;wire[31:0]alloc_rsp_base;
 wire x_req_valid,x_req_ready,x_valid,x_ready,x_error;wire[15:0]x_req_record,x_record;
 wire[6:0]x_req_base,x_ordinal;wire[7:0]x_req_extent;wire[3:0]x_group;wire[2047:0]x_data;
 wire publication_valid,publication_ready,source_publication_valid,source_publication_ready,barrier_fault;wire[15:0]publication_record;
 wire req_v,req_ready,rsp_v,rv;wire[31:0]req_addr;wire[9:0]req_tag,rsp_tag;wire[1087:0]rsp_data;
 wire[11:0]rrow;wire[255:0]rdata;wire native_arrive,native_fault,native_compute_fault;
 wire allocation_fault,program_fault,weight_fault,x_fault,result_fault;
 wire peer_fault=barrier_fault||context_fault||service_fault||allocation_fault||program_fault||weight_fault||x_fault||result_fault;
 assign fault=native_fault||peer_fault;
 wire tuple_found;wire[31:0]weight_base;wire[32:0]weight_limit;
 wire[36:0]x_base,result_base,result_limit;wire[37:0]x_limit;wire[7:0]x_extent;wire[6:0]x_ring;wire[12:0]result_rows;
 ot_hbm_sm_native_tuple tuple(.record_id(alloc_record),.found(tuple_found),.*);
 wire reserve_v,reserve_r,source_permit,retained,rom_req_ready,rom_rsp_valid;
 wire installed_tuple=installed&&context_live&&tuple_found&&!context_fault;
 assign c_req_context={4{{context_q[77:5],alloc_record,context_q[4:0]}}};
 assign reserve_v=alloc_valid&&rom_req_ready&&installed_tuple&&!peer_fault;
 assign alloc_ready=reserve_r&&rom_req_ready&&installed_tuple&&!peer_fault;
 assign alloc_rsp_valid=rom_rsp_valid&&source_permit&&!peer_fault;
 ot_hbm_sm_native_allocation #(.ENABLE(ENABLE)) allocation(
 .clk(clk),.rst_n(rst_n),.req_valid(alloc_valid&&reserve_r&&installed_tuple&&!peer_fault),.req_ready(rom_req_ready),
 .req_record(alloc_record),.req_lines(alloc_lines),.rsp_valid(rom_rsp_valid),.rsp_ready(alloc_rsp_ready&&source_permit&&!peer_fault),
 .rsp_record(alloc_rsp_record),.rsp_base(alloc_rsp_base),.rsp_error(alloc_rsp_error),.fault(allocation_fault));
 ot_hbm_sm_native_provider_leaf #(.ENABLE(ENABLE),.PROTECT(PROTECT),.DESC_HOPS(DESC_HOPS)) native(
 .fault(native_fault),.run_valid(native_run_valid),.run_ready(native_run_ready),.*);
 // Actual arrival toggle is observed at the fast clock, never fabricated by a timer.
 (* keep=1,dont_touch=1 *)reg arrive_seen,arrive_seen_n;always @(posedge clk or negedge rst_n)if(!rst_n)begin arrive_seen<=0;arrive_seen_n<=1;end else begin arrive_seen<=native_arrive;arrive_seen_n<=~native_arrive;end
 wire native_done=native_arrive!=arrive_seen;
 ot_hbm_sm_program_word #(.ENABLE(ENABLE)) program_reader(
 .clk(clk),.rst_n(rst_n),.region_valid(installed&&context_live&&!context_fault),.virtual_base(program_base),.virtual_limit(program_storage_limit),
 .physical_base({5'b0,program_base}),.request_tag(held_issuer_tag),
 .mem_req_valid(mem_req_valid),.mem_req_ready(mem_req_ready),.mem_req_addr(mem_req_addr),
 .mem_rsp_valid(mem_rsp_valid),.mem_rsp_ready(mem_rsp_ready),.mem_rsp_addr(mem_rsp_addr),.mem_rsp_data(mem_rsp_data),.mem_rsp_error(mem_rsp_error),
 .service_req_valid(c_req_v[0]),.service_req_ready(c_req_r[0]),.service_req_addr(c_req_addr[0+:37]),.service_req_tag(c_req_tag[0+:16]),
 .service_rsp_valid(c_rsp_v[0]),.service_rsp_ready(c_rsp_r[0]),.service_rsp_we(c_rsp_we[0]),.service_rsp_tag(c_rsp_tag[0+:16]),.service_rsp_data(c_rsp_data[0+:256]),
 .service_fault(service_fault||context_fault||c_rsp_error[0]),.fault(program_fault));
 ot_hbm_sm_weight_read #(.ENABLE(ENABLE)) weight_reader(
 .clk(clk),.rst_n(rst_n),.installed_valid(installed_tuple),.installed_line_base(weight_base),.installed_line_limit(weight_limit),
 .req_v(req_v),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),.rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),.issuer_tag(held_issuer_tag),
 .service_req_valid(c_req_v[1]),.service_req_ready(c_req_r[1]),.service_req_addr(c_req_addr[37+:37]),.service_req_tag(c_req_tag[16+:16]),
 .service_rsp_valid(c_rsp_v[1]),.service_rsp_ready(c_rsp_r[1]),.service_rsp_we(c_rsp_we[1]),.service_rsp_tag(c_rsp_tag[16+:16]),.service_rsp_data(c_rsp_data[256+:256]),
 .service_fault(service_fault||context_fault||c_rsp_error[1]),.fault(weight_fault));
 ot_hbm_sm_x_read #(.ENABLE(ENABLE)) x_reader(
 .clk(clk),.rst_n(rst_n),.installed_valid(installed_tuple),.installed_base(x_base),.installed_limit(x_limit),
 .installed_record(alloc_record),.installed_extent(x_extent),.installed_ring(x_ring),
 .x_req_valid(x_req_valid),.x_req_ready(x_req_ready),.x_req_record(x_req_record),.x_req_base(x_req_base),.x_req_extent(x_req_extent),
 .x_valid(x_valid),.x_ready(x_ready),.x_record(x_record),.x_ordinal(x_ordinal),.x_group(x_group),.x_data(x_data),.x_error(x_error),.issuer_tag(held_issuer_tag),
 .service_req_valid(c_req_v[2]),.service_req_ready(c_req_r[2]),.service_req_addr(c_req_addr[74+:37]),.service_req_tag(c_req_tag[32+:16]),
 .service_rsp_valid(c_rsp_v[2]),.service_rsp_ready(c_rsp_r[2]),.service_rsp_we(c_rsp_we[2]),.service_rsp_tag(c_rsp_tag[32+:16]),.service_rsp_data(c_rsp_data[512+:256]),
 .service_fault(service_fault||context_fault||c_rsp_error[2]),.fault(x_fault));
 assign c_req_we[2:0]=0;assign c_req_data[767:0]=0;
 ot_hbm_sm_result_provider #(.ENABLE(ENABLE)) results(
 .clk(clk),.por_n(rst_n),.installed(installed_tuple&&!native_compute_fault&&!service_fault&&!(allocation_fault||program_fault||weight_fault||x_fault)),
 .reserve_v(reserve_v),.reserve_r(reserve_r),.record_id(alloc_record),.provider_tag(held_issuer_tag),
 .rows(result_rows),.base(result_base),.limit(result_limit),.source_permit(source_permit),.retained(retained),.fault(result_fault),
 .result_v(rv),.result_row(rrow),.result_data(rdata),.native_done(native_done),
 .publication_v(source_publication_valid),.publication_r(source_publication_ready),.publication_record(publication_record),
 .req_v(c_req_v[3]),.req_r(c_req_r[3]),.req_we(c_req_we[3]),.req_addr(c_req_addr[111+:37]),.req_data(c_req_data[768+:256]),.req_tag(c_req_tag[48+:16]),
 .rsp_v(c_rsp_v[3]),.rsp_r(c_rsp_r[3]),.rsp_we(c_rsp_we[3]),.rsp_tag(c_rsp_tag[48+:16]),.rsp_data(c_rsp_data[768+:256]),.rsp_error(c_rsp_error[3]));
ot_hbm_sm_publication_barrier #(.ENABLE(ENABLE)) barrier(
 .clk(clk),.rst_n(rst_n),.source_valid(source_publication_valid),.source_ready(source_publication_ready),
 .source_context({context_q[77:5],publication_record,context_q[4:0]}),
 .su_publication_valid(su_publication_valid),.su_publication_ready(su_publication_ready),.su_publication_context(su_publication_context),
 .su_release_valid(su_release_valid),.su_release_ready(su_release_ready),.su_release_context(su_release_context),
 .owner_valid(publication_valid),.owner_ready(publication_ready),.fault(barrier_fault));
endmodule
