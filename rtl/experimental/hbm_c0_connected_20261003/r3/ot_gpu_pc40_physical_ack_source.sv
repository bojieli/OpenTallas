// Default-off direct-RF source connector, selected PC40/tile0. Real provider
// ports, current W6 and literal FMIN consumer; response route owned until capture.
// Parent grants exclusive RF workspace/port ownership via issuer_binding_valid.
// This is not a W2/R14 address/tag adapter and does not allocate HBM identity.
module ot_gpu_pc40_physical_ack_source #(parameter bit ENABLE=0)(
 input wire clk,por_n,rst_n,req_valid,output wire req_ready,
 input wire[45:0]req_owner46,input wire[63:0]req_native_tag,req_native_generation,
 input wire issuer_binding_valid,visibility_enable,
 output wire rd_valid,input wire rd_ready,output wire[8:0]rd_a,rd_b,
 input wire rsp_valid,input wire[4095:0]rsp_a,rsp_b,output wire rsp_ready,
 output wire wr_valid,input wire wr_ready,output wire[8:0]wr_addr,output wire[4095:0]wr_data,
 input wire ack_valid,output wire ack_ready,
 input wire[45:0]ack_owner,input wire[8:0]ack_slot,input wire ack_identity_fault,
 output wire[45:0]wr_owner,output wire ack_integration_fault,
 output wire visible_valid,output wire[54:0]visible_identity,
 output wire result_valid,input wire result_ready,output wire[4095:0]result,
 output wire consumer_accepted,output wire[54:0]consumer_identity,
 input wire child_reverse_valid,input wire[54:0]child_reverse_identity,output wire child_reverse_ready,
 input wire parent_reverse_valid,input wire[54:0]parent_reverse_identity,output wire parent_reverse_ready,
 input wire reverse_CDC_valid,input wire[54:0]reverse_CDC_identity,output wire reverse_CDC_ready,
 output wire drain_req_valid,output wire[54:0]drain_req_identity,output wire drain_req_has_owner,drain_req_reset_scope,
 input wire drain_req_ready,drain_rsp_valid,input wire[54:0]drain_rsp_identity,
 input wire drain_rsp_has_owner,drain_rsp_reset_scope,input wire[8:0]alldrain_live,output wire drain_rsp_ready,
 output wire done_valid,input wire done_ready,output wire[63:0]done_native_tag,done_native_generation,
 input wire rearm_valid,admission_stop,issuer_allcopy_fenced,output wire rearm_ready,exclusive_lease,fault
);
 wire b_wr_valid,b_ack_ready,b_done_valid,b_rd_valid,b_rd_ready,b_rsp_ready,b_fault,c_fault,c_busy,c_rd_valid,c_rd_ready,c_rsp_ready,c_visible_ready,c_accept,c_ready,c_result_valid;
 wire[8:0]b_rd_a,b_rd_b,c_rd_a,c_rd_b;
 wire[1:0]consumer_ready,child_ready,parent_ready,cdc_ready,dreq_valid,dreq_has,dreq_scope,drsp_ready;
 wire[109:0]dreq_identity;
 assign fault=b_fault||c_fault;assign ack_integration_fault=fault;
 assign wr_valid=b_wr_valid&&!fault;assign ack_ready=b_ack_ready&&!fault;assign done_valid=b_done_valid&&!fault;
 assign rd_valid=!fault && (c_busy?c_rd_valid:b_rd_valid);
 assign rd_a=c_busy?c_rd_a:b_rd_a;assign rd_b=c_busy?c_rd_b:b_rd_b;
 assign b_rd_ready=rd_ready&&!c_busy&&!fault;assign c_rd_ready=rd_ready&&c_busy&&!fault;
 assign rsp_ready=!fault && (c_busy?c_rsp_ready:b_rsp_ready);
 assign result_valid=c_result_valid&&!b_fault;
 assign consumer_accepted=!fault&&c_accept&&consumer_ready[0];
 assign child_reverse_ready=!fault&&child_ready[0];assign parent_reverse_ready=!fault&&parent_ready[0];assign reverse_CDC_ready=!fault&&cdc_ready[0];
 assign drain_req_valid=dreq_valid[0];assign drain_req_identity=dreq_identity[54:0];
 assign drain_req_has_owner=dreq_has[0];assign drain_req_reset_scope=dreq_scope[0];assign drain_rsp_ready=drsp_ready[0];
 ot_gpu_c0_connected_bridge_r3 #(.ENABLE(ENABLE))bridge(
 .clk(clk),.por_n(por_n),.rst_n(rst_n),.req_valid(req_valid&&!c_fault),.req_ready(req_ready),
 .req_owner46(req_owner46),.req_native_tag(req_native_tag),.req_native_generation(req_native_generation),
 .issuer_binding_valid(issuer_binding_valid&&rd_ready&&wr_ready&&!ack_valid&&!rsp_valid&&!c_busy&&!c_fault),
 .local_rd_valid(b_rd_valid),.local_rd_ready(b_rd_ready),.local_rd_a(b_rd_a),.local_rd_b(b_rd_b),
 .local_rsp_valid(rsp_valid&&!c_busy),.local_rsp_a(rsp_a),.local_rsp_b(rsp_b),.local_rsp_ready(b_rsp_ready),
 .local_wr_valid(b_wr_valid),.local_wr_ready(wr_ready&&!c_fault),.local_wr_addr(wr_addr),.local_wr_data(wr_data),
 .local_ack_valid(ack_valid),.local_ack_ready(b_ack_ready),
 .local_ack_owner(ack_owner),.local_ack_slot(ack_slot),.local_ack_identity_fault(ack_identity_fault),.local_wr_owner(wr_owner),
 .remote_wr_valid(),.remote_wr_ready(1'b0),.remote_wr_addr(),.remote_wr_data(),.remote_ack_valid(1'b0),.remote_ack_ready(),
 .visible_valid(visible_valid),.visible_ready(visibility_enable&&c_visible_ready),.visible_identity(visible_identity),
 .consumer_valid({1'b0,c_accept}),.consumer_ready(consumer_ready),.consumer_identity({55'd0,consumer_identity}),
 .child_reverse_valid({1'b0,child_reverse_valid}),.child_reverse_ready(child_ready),.child_reverse_identity({55'd0,child_reverse_identity}),
 .parent_reverse_valid({1'b0,parent_reverse_valid}),.parent_reverse_ready(parent_ready),.parent_reverse_identity({55'd0,parent_reverse_identity}),
 .reverse_CDC_valid({1'b0,reverse_CDC_valid}),.reverse_CDC_ready(cdc_ready),.reverse_CDC_identity({55'd0,reverse_CDC_identity}),
 .drain_req_valid(dreq_valid),.drain_req_identity(dreq_identity),.drain_req_has_owner(dreq_has),.drain_req_reset_scope(dreq_scope),.drain_req_ready({1'b0,drain_req_ready}),
 .drain_rsp_valid({1'b0,drain_rsp_valid}),.drain_rsp_ready(drsp_ready),.drain_rsp_identity({55'd0,drain_rsp_identity}),
 .drain_rsp_has_owner({1'b0,drain_rsp_has_owner}),.drain_rsp_reset_scope({1'b0,drain_rsp_reset_scope}),.alldrain_live({9'd0,alldrain_live}),
 .done_valid(b_done_valid),.done_ready(done_ready&&!c_fault),.done_native_tag(done_native_tag),.done_native_generation(done_native_generation),
 .rearm_valid(rearm_valid),.admission_stop(admission_stop||fault),.issuer_allcopy_fenced(issuer_allcopy_fenced),.rearm_ready(rearm_ready),.exclusive_lease(exclusive_lease),.fault(b_fault));
 ot_gpu_pc40_fmin_consumer #(.ENABLE(ENABLE))consumer(
 .clk(clk),.por_n(por_n),.rst_n(rst_n),.visible_valid(visible_valid&&visibility_enable&&!b_fault),.visible_ready(c_visible_ready),.visible_identity(visible_identity),
 .rd_valid(c_rd_valid),.rd_ready(c_rd_ready),.rd_a(c_rd_a),.rd_b(c_rd_b),
 .rsp_valid(rsp_valid&&c_busy),.rsp_a(rsp_a),.rsp_ready(c_rsp_ready),
 .result_valid(c_result_valid),.result_ready(result_ready&&!b_fault),.result(result),
 .consumer_valid(c_accept),.consumer_ready(consumer_ready[0]&&!b_fault),.consumer_identity(consumer_identity),.busy(c_busy),.fault(c_fault));
endmodule
