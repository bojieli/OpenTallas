`timescale 1ns/1ps
// Dedicated W2 source cut: existing caller output flops, sector service, one
// shared protected owner, AW3 crossing and root-POR/local-CP-reset boundary.
// Preparation is not physical admission. Inherited CDC protection and actual
// driver/receiver placement/clock/load bindings remain mandatory model holds.
module ot_hbm_w2_protected_parent_context #(
 parameter integer ENABLE=0, PROTECTED_TRANSACTION_PIPELINE=0
)(
 input wire clk_sm,rst_sm_n,clk_mem,rst_mem_n,
 input wire cp_reset_req,cp_idle,cp_cpl_v,cp_cpl_rdy,
 output wire cp_reset_n,cp_reset_ack,cp_reset_wait,all_routes_drained,
 output wire qualified_cpl_v,qualified_cpl_rdy,
 input wire installed,weights_installed,reserve_v,
 output wire reserve_r,source_permit,retained,done,
 input wire pair_op,input wire [1:0] rows_a,rows_b,
 input wire [31:0] op_a,op_b,base_a,limit_a,base_b,limit_b,
 input wire [15:0] provider_tag,input wire [72:0] frame,
 // D-side cuts at actual PQ result/valid output registers, not oracle inputs.
 input wire producer_cv,producer_fault,
 input wire [7:0] producer_crow,input wire [255:0] producer_cy,
 input wire producer_busy,producer_arrive,producer_released,
 input wire caller_start,caller_sm_ready,caller_pair,caller_bound,
 input wire [8:0] caller_rows,input wire [31:0] caller_op_a,caller_op_b,
 output wire caller_ctx_ready,caller_busy,caller_arrive,caller_released,
 input wire native_done,
 // Actual enclosing W2 lease/release and other active borrower/native cuts.
 input wire lease_v,release_v,input wire [72:0] release_frame,
 output wire lease_granted,release_r,
 input wire [1:0] other_lease_v,other_quiet,other_release_v,
 input wire [63:0] other_lease_job,other_release_job,
 input wire [7:0] other_lease_gen,other_release_gen,
 input wire [33:0] other_lease_token,other_release_token,
 input wire [39:0] other_lease_pos,other_release_pos,
 output wire [1:0] other_grants,other_releases,
 input wire native_clients_drained,cdc_drained,other_routes_drained,w2_quiet,
 input wire [3:0] observe_req,observe_rsp,observe_req_we,observe_rsp_we,return_offer,
 input wire [63:0] observe_req_tag,observe_rsp_tag,
 input wire [31:0] native_job,input wire [3:0] native_gen,
 input wire [16:0] native_token,input wire [19:0] native_pos,
 output wire [3:0] response_authorized,
 input wire [2:0] other_req_v,other_req_we,other_rsp_rdy,
 input wire [95:0] other_req_addr,other_req_wstrb,
 input wire [767:0] other_req_wdata,input wire [47:0] other_req_tag,
 output wire [2:0] other_req_rdy,other_rsp_v,other_rsp_we,
 output wire [47:0] other_rsp_tag,output wire [767:0] other_rsp_data,
 input wire native_req_v,output wire native_req_r,
 input wire [31:0] native_req_addr,input wire [9:0] native_req_tag,
 input wire map_valid,input wire [72:0] map_frame,
 input wire [31:0] map_native_addr,input wire [2:0] map_sm,
 input wire [15:0] map_compact_offset,input wire [3:0] map_lanes,
 input wire [2:0] map_count,input wire [191:0] map_byte_addresses,
 input wire [95:0] map_tags,map_cfg,input wire native_delivery_permit,
 output wire native_rsp_pending,native_rsp_v,
 output wire [9:0] native_rsp_tag,output wire [1087:0] native_rsp_data,
 output wire m_req_v,input wire m_req_rdy,output wire m_req_we,
 output wire [31:0] m_req_addr,m_req_wstrb,output wire [255:0] m_req_wdata,
 output wire [15:0] m_req_tag,
 input wire m_rsp_v,output wire m_rsp_rdy,input wire m_rsp_we,
 input wire [15:0] m_rsp_tag,input wire [255:0] m_rsp_data,
 output wire fault
);
 wire result_v,caller_fault;wire [7:0] caller_row;
 wire [31:0] result_op;wire [255:0] result_data;
 ot_hbm_w2_existing_caller_result_cut #(.ENABLE(ENABLE)) u_caller_cut(
  .clk(clk_sm),.rst_n(rst_sm_n),.producer_cv(producer_cv),.producer_fault(producer_fault),
  .producer_crow(producer_crow),.producer_cy(producer_cy),
  .producer_busy(producer_busy),.producer_arrive(producer_arrive),.producer_released(producer_released),
  .caller_start(caller_start),.caller_sm_ready(caller_sm_ready),.caller_pair(caller_pair),
  .caller_bound(caller_bound),.caller_rows(caller_rows),.caller_op_a(caller_op_a),.caller_op_b(caller_op_b),
  .ctx_ready(caller_ctx_ready),.rv(result_v),.rrow(caller_row),.rop(result_op),.rdata(result_data),
  .busy(caller_busy),.arrive(caller_arrive),.released(caller_released),.fault(caller_fault));
 wire sink_req_v,sink_req_r,sink_rsp_v,sink_rsp_r,sink_retire_r,sink_fault;
 wire [336:0] sink_req;wire [272:0] provider_rsp;
 wire adapter_req_v,adapter_req_r,adapter_rsp_v,adapter_rsp_r,adapter_busy,adapter_drained,adapter_fault,foreign_rsp;
 wire [336:0] adapter_req;
 wire [2:0] grants,releases;wire shared_idle,native_credit_empty,shared_fault;
 assign lease_granted=grants[2];assign other_grants=grants[1:0];assign other_releases=releases[1:0];
 assign release_r=releases[2]&&adapter_drained&&sink_retire_r;
 ot_hbm_integrated_w2_result_sink #(.ENABLE(ENABLE),.PROTECTED_TRANSACTION_PIPELINE(PROTECTED_TRANSACTION_PIPELINE)) u_w2_sink(
  .clk(clk_sm),.por_n(rst_sm_n),.owned(grants[2]),.installed(installed),
  .reserve_v(reserve_v),.reserve_r(reserve_r),.pair_op(pair_op),.rows_a(rows_a),.rows_b(rows_b),
  .op_a(op_a),.op_b(op_b),.base_a(base_a),.limit_a(limit_a),.base_b(base_b),.limit_b(limit_b),
  .provider_tag(provider_tag),.frame(frame),.source_permit(source_permit),.retained(retained),.done(done),.quiet(),.fault(sink_fault),
  .result_v(result_v),.result_op(result_op),.result_row({4'b0,caller_row}),.result_data(result_data),
  .native_done(native_done),.retire_v(release_v&&releases[2]),.retire_r(sink_retire_r),
  .req_v(sink_req_v),.req_r(sink_req_r&&adapter_drained),.req(sink_req),
  .rsp_v(sink_rsp_v),.rsp_r(sink_rsp_r),.rsp(provider_rsp));
 ot_hbm_integrated_w2_sector_adapter #(.ENABLE(ENABLE)) u_w2_sectors(
  .clk(clk_sm),.por_n(rst_sm_n),.owner_valid(grants[2]),.owner_frame(frame),
  .source_accept_permit(source_permit&&weights_installed),.result_seat_permit(source_permit),
  .native_req_v(native_req_v),.native_req_r(native_req_r),.native_req_addr(native_req_addr),.native_req_tag(native_req_tag),
  .map_valid(map_valid&&weights_installed),.map_frame(map_frame),.map_native_addr(map_native_addr),.map_sm(map_sm),
  .map_compact_offset(map_compact_offset),.map_lanes(map_lanes),.map_count(map_count),
  .map_byte_addresses(map_byte_addresses),.map_tags(map_tags),.map_cfg(map_cfg),
  .sector_req_v(adapter_req_v),.sector_req_r(adapter_req_r),.sector_req(adapter_req),
  .sector_rsp_v(adapter_rsp_v),.sector_rsp_r(adapter_rsp_r),.sector_rsp(provider_rsp),
  .native_delivery_permit(native_delivery_permit),.native_rsp_pending(native_rsp_pending),
  .native_rsp_v(native_rsp_v),.native_rsp_tag(native_rsp_tag),.native_rsp_data(native_rsp_data),
  .busy(adapter_busy),.drained(adapter_drained),.fault(adapter_fault),.foreign_rsp(foreign_rsp));
 wire [3:0] req_rdy,rsp_v,rsp_we;wire [63:0] rsp_tag;wire [1023:0] rsp_data;
 wire sink_route=sink_req_v&&adapter_drained;
 wire sink_response=adapter_drained&&retained;
 assign sink_req_r=req_rdy[3]&&sink_route;assign adapter_req_r=req_rdy[3]&&!sink_route;
 assign sink_rsp_v=rsp_v[3]&&sink_response;assign adapter_rsp_v=rsp_v[3]&&!sink_response;
 assign provider_rsp={rsp_tag[63:48],rsp_we[3],rsp_data[1023:768]};
 assign other_req_rdy=req_rdy[2:0];assign other_rsp_v=rsp_v[2:0];assign other_rsp_we=rsp_we[2:0];
 assign other_rsp_tag=rsp_tag[47:0];assign other_rsp_data=rsp_data[767:0];
 wire c_req_v,c_req_rdy,c_req_we,c_rsp_v,c_rsp_rdy,c_rsp_we;
 wire [31:0] c_req_addr,c_req_wstrb;wire [255:0] c_req_wdata,c_rsp_data;wire [15:0] c_req_tag,c_rsp_tag;
 wire [336:0] selected_req=sink_route?sink_req:adapter_req;
 ot_hbm_integrated_sm0_borrow #(.ENABLE(ENABLE)) u_shared_owner(
  .clk(clk_sm),.por_n(rst_sm_n),.native_clients_drained(native_clients_drained),.cdc_drained(cdc_drained),
  .observe_req(observe_req),.observe_rsp(observe_rsp),.observe_req_we(observe_req_we),.observe_rsp_we(observe_rsp_we),
  .observe_req_tag(observe_req_tag),.observe_rsp_tag(observe_rsp_tag),.return_offer(return_offer),.response_authorized(response_authorized),
  .native_job(native_job),.native_gen(native_gen),.native_token(native_token),.native_pos(native_pos),
  .native_credit_empty(native_credit_empty),.lease_v({lease_v,other_lease_v}),
  .borrower_quiet({!retained&&adapter_drained,other_quiet}),
  .lease_job({frame[31:0],other_lease_job}),.lease_gen({frame[35:32],other_lease_gen}),
  .lease_token({frame[52:36],other_lease_token}),.lease_pos({frame[72:53],other_lease_pos}),
  .lease_granted(grants),.release_v({release_v&&adapter_drained&&sink_retire_r,other_release_v}),.release_r(releases),
  .release_job({release_frame[31:0],other_release_job}),.release_gen({release_frame[35:32],other_release_gen}),
  .release_token({release_frame[52:36],other_release_token}),.release_pos({release_frame[72:53],other_release_pos}),
  .req_v({sink_route||adapter_req_v,other_req_v}),.req_rdy(req_rdy),.req_we({selected_req[336],other_req_we}),
  .req_addr({selected_req[335:304],other_req_addr}),.req_wdata({selected_req[303:48],other_req_wdata}),
  .req_wstrb({selected_req[47:16],other_req_wstrb}),.req_tag({selected_req[15:0],other_req_tag}),
  .rsp_v(rsp_v),.rsp_rdy({sink_response?sink_rsp_r:adapter_rsp_r,other_rsp_rdy}),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
  .m_req_v(c_req_v),.m_req_rdy(c_req_rdy),.m_req_we(c_req_we),.m_req_addr(c_req_addr),.m_req_wdata(c_req_wdata),
  .m_req_wstrb(c_req_wstrb),.m_req_tag(c_req_tag),.m_rsp_v(c_rsp_v),.m_rsp_rdy(c_rsp_rdy),.m_rsp_we(c_rsp_we),
  .m_rsp_tag(c_rsp_tag),.m_rsp_data(c_rsp_data),.idle(shared_idle),.fault(shared_fault));
 ot_gpu_mreq_cdc #(.ENABLE(ENABLE),.AW(3)) u_existing_cdc(
  .clk_s(clk_sm),.rst_s_n(rst_sm_n),.clk_m(clk_mem),.rst_m_n(rst_mem_n),
  .s_req_v(c_req_v),.s_req_rdy(c_req_rdy),.s_req_we(c_req_we),.s_req_addr(c_req_addr),
  .s_req_wdata(c_req_wdata),.s_req_wstrb(c_req_wstrb),.s_req_tag(c_req_tag),
  .s_rsp_v(c_rsp_v),.s_rsp_rdy(c_rsp_rdy),.s_rsp_tag(c_rsp_tag),.s_rsp_we(c_rsp_we),.s_rsp_data(c_rsp_data),
  .m_req_v(m_req_v),.m_req_rdy(m_req_rdy),.m_req_we(m_req_we),.m_req_addr(m_req_addr),.m_req_wdata(m_req_wdata),
  .m_req_wstrb(m_req_wstrb),.m_req_tag(m_req_tag),.m_rsp_v(m_rsp_v),.m_rsp_rdy(m_rsp_rdy),
  .m_rsp_tag(m_rsp_tag),.m_rsp_we(m_rsp_we),.m_rsp_data(m_rsp_data),.fault(cdc_fault));
 wire cdc_fault,reset_fault;
 // As in the selected enclosing parent: local CP reset never touches owner,
 // publication, sector or either CDC root reset. Drain facts remain real cuts.
 assign all_routes_drained=native_credit_empty&&shared_idle&&adapter_drained&&w2_quiet&&!retained&&other_routes_drained;
 assign qualified_cpl_v=cp_cpl_v&&all_routes_drained;
 assign qualified_cpl_rdy=cp_cpl_rdy&&all_routes_drained;
 ot_hbm_integrated_cp_reset #(.ENABLE(ENABLE)) u_cp_reset(
  .clk(clk_sm),.por_n(rst_sm_n),.reset_req(cp_reset_req),.cp_idle(cp_idle),.routes_drained(all_routes_drained),
  .cp_reset_n(cp_reset_n),.reset_ack(cp_reset_ack),.block_new(cp_reset_wait),.fault(reset_fault));
 assign fault=sink_fault|adapter_fault|shared_fault|cdc_fault|reset_fault|caller_fault;
endmodule

// Verbatim PQ output-register topology and the caller's existing identity join.
// NC8/RMAX256/PIO2 are the released selected shape. No new payload queue,
// protection waiver, capture edge, start ledger, or callback-ready interface.
module ot_hbm_w2_existing_caller_result_cut #(parameter integer ENABLE=0)(
 input wire clk,rst_n,producer_cv,producer_fault,
 input wire [7:0] producer_crow,input wire [255:0] producer_cy,
 input wire producer_busy,producer_arrive,producer_released,
 input wire caller_start,caller_sm_ready,caller_pair,caller_bound,
 input wire [8:0] caller_rows,input wire [31:0] caller_op_a,caller_op_b,
 output wire ctx_ready,rv,output wire [7:0] rrow,output wire [31:0] rop,
 output wire [255:0] rdata,output wire busy,arrive,released,fault
);
 generate if(!ENABLE)begin:off
 assign ctx_ready=0;assign rv=0;assign rrow=0;assign rop=0;assign rdata=0;
 assign busy=0;assign arrive=0;assign released=0;assign fault=0;
 end else begin:on
 reg rv_q,fault_q;reg [7:0] rrow_q;reg [255:0] rdata_q;
 wire sm_rv,sm_fault,ctx_fault;wire [7:0] sm_row;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin rv_q<=0;fault_q<=0;end
  else begin rv_q<=producer_cv;fault_q<=fault_q|producer_fault;end
 always @(posedge clk)begin rrow_q<=producer_crow;rdata_q<=producer_cy;end
 ot_hbm_accel_smv_chain #(.W(2),.D(2),.RST(1)) u_prv_o(
  .clk(clk),.rst_n(rst_n),.d({rv_q,fault_q}),.q({sm_rv,sm_fault}));
 ot_hbm_accel_smv_chain #(.W(264),.D(2),.RST(0)) u_prd_o(
  .clk(clk),.rst_n(rst_n),.d({rrow_q,rdata_q}),.q({sm_row,rdata}));
 ot_hbm_accel_smv_chain #(.W(3),.D(2),.RST(1)) u_pbz(
  .clk(clk),.rst_n(rst_n),.d({producer_busy,producer_arrive,producer_released}),.q({busy,arrive,released}));
 ot_hbm_accel_w2_result_join #(.ENABLE(1),.RW(8)) u_results(
  .clk(clk),.rst_n(rst_n),.ctx_valid(caller_start&&caller_sm_ready),.ctx_ready(ctx_ready),
  .ctx_pair(caller_pair),.ctx_bound(caller_bound),.ctx_rows(caller_rows),
  .ctx_op_a(caller_op_a),.ctx_op_b(caller_op_b),.rsp_v(sm_rv),.rsp_row(sm_row),
  .out_v(rv),.out_row(rrow),.out_operation(rop),.pair_complete(),.fault(ctx_fault));
 assign fault=sm_fault|ctx_fault;
 end endgenerate
endmodule
