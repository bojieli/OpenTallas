// Simulation port top: existing modeled RF/ACK_ID1/W6 source, default off.
// No new engine state or physical admission. Drive real system authorities.
module ot_gpu_pc40_native_sim_port_r5 #(parameter bit ENABLE=0)(
 input wire clk,por_n,rst_n,
 input wire publish_valid,output wire publish_ready,input wire[4095:0]publish_data,
 input wire[45:0]publish_owner46,input wire[63:0]publish_native_tag,publish_native_generation,
 input wire source_lease_reserved,workspace_reserved,issuer_namespace_reserved,
 input wire source_release_valid,input wire[54:0]source_release_identity,
 output wire source_release_ready,source_lease_live,workspace_lease_live,source_published,
 input wire issuer_binding_valid,visibility_enable,
 output wire ack_integration_fault,
 output wire rf_read_accepted,rf_response_accepted,rf_write_accepted,rf_ACK_accepted,
 output wire[8:0]rf_read_a,rf_read_b,rf_write_slot,
 output wire[4095:0]rf_response_a,rf_response_b,
 output wire[45:0]rf_write_owner,rf_ACK_owner,
 output wire[8:0]rf_ACK_slot,output wire rf_ACK_fault,
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
 wire rd_valid,rd_ready,rsp_valid,rsp_ready,wr_valid,wr_ready,ack_valid,ack_ready,ack_identity_fault;
 wire[8:0]rd_a,rd_b,wr_addr,ack_slot;
 wire[4095:0]rsp_a,rsp_b,wr_data;
 wire[45:0]wr_owner,ack_owner;
 // Observer wires expose actual handshakes, not elapsed-time acknowledgments.
 assign rf_read_accepted=rd_valid&&rd_ready;
 assign rf_response_accepted=rsp_valid&&rsp_ready;
 assign rf_write_accepted=wr_valid&&wr_ready;
 assign rf_ACK_accepted=ack_valid&&ack_ready;
 assign rf_read_a=rd_a;assign rf_read_b=rd_b;assign rf_write_slot=wr_addr;
 assign rf_response_a=rsp_a;assign rf_response_b=rsp_b;
 assign rf_write_owner=wr_owner;assign rf_ACK_owner=ack_owner;
 assign rf_ACK_slot=ack_slot;assign rf_ACK_fault=ack_identity_fault;
 ot_gpu_pc40_native_connector_r5 #(.ENABLE(ENABLE)) connector(
.clk(clk),
.por_n(por_n),
.rst_n(rst_n),
.publish_valid(publish_valid),
.publish_ready(publish_ready),
.publish_data(publish_data),
.publish_owner46(publish_owner46),
.publish_native_tag(publish_native_tag),
.publish_native_generation(publish_native_generation),
.source_lease_reserved(source_lease_reserved),
.workspace_reserved(workspace_reserved),
.issuer_namespace_reserved(issuer_namespace_reserved),
.source_release_valid(source_release_valid),
.source_release_identity(source_release_identity),
.source_release_ready(source_release_ready),
.source_lease_live(source_lease_live),
.workspace_lease_live(workspace_lease_live),
.source_published(source_published),
.issuer_binding_valid(issuer_binding_valid),
.visibility_enable(visibility_enable),
.rd_valid(rd_valid),
.rd_ready(rd_ready),
.rd_a(rd_a),
.rd_b(rd_b),
.rsp_valid(rsp_valid),
.rsp_a(rsp_a),
.rsp_b(rsp_b),
.rsp_ready(rsp_ready),
.wr_valid(wr_valid),
.wr_ready(wr_ready),
.wr_addr(wr_addr),
.wr_data(wr_data),
.ack_valid(ack_valid),
.ack_ready(ack_ready),
.ack_owner(ack_owner),
.ack_slot(ack_slot),
.ack_identity_fault(ack_identity_fault),
.wr_owner(wr_owner),
.ack_integration_fault(ack_integration_fault),
.visible_valid(visible_valid),
.visible_identity(visible_identity),
.result_valid(result_valid),
.result_ready(result_ready),
.result(result),
.consumer_accepted(consumer_accepted),
.consumer_identity(consumer_identity),
.child_reverse_valid(child_reverse_valid),
.child_reverse_identity(child_reverse_identity),
.child_reverse_ready(child_reverse_ready),
.parent_reverse_valid(parent_reverse_valid),
.parent_reverse_identity(parent_reverse_identity),
.parent_reverse_ready(parent_reverse_ready),
.reverse_CDC_valid(reverse_CDC_valid),
.reverse_CDC_identity(reverse_CDC_identity),
.reverse_CDC_ready(reverse_CDC_ready),
.drain_req_valid(drain_req_valid),
.drain_req_identity(drain_req_identity),
.drain_req_has_owner(drain_req_has_owner),
.drain_req_reset_scope(drain_req_reset_scope),
.drain_req_ready(drain_req_ready),
.drain_rsp_valid(drain_rsp_valid),
.drain_rsp_identity(drain_rsp_identity),
.drain_rsp_has_owner(drain_rsp_has_owner),
.drain_rsp_reset_scope(drain_rsp_reset_scope),
.alldrain_live(alldrain_live),
.drain_rsp_ready(drain_rsp_ready),
.done_valid(done_valid),
.done_ready(done_ready),
.done_native_tag(done_native_tag),
.done_native_generation(done_native_generation),
.rearm_valid(rearm_valid),
.admission_stop(admission_stop),
.issuer_allcopy_fenced(issuer_allcopy_fenced),
.rearm_ready(rearm_ready),
.exclusive_lease(exclusive_lease),
.fault(fault)
 );
 generate if(ENABLE)begin:provider
 ot_gpu_rf_service #(.ACK_ID(1)) rf(
 .clk(clk),.rst_n(rst_n),.rd_valid(rd_valid),.rd_ready(rd_ready),.rd_a(rd_a),.rd_b(rd_b),
 .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_a(rsp_a),.rsp_b(rsp_b),
 .wr_valid(wr_valid),.wr_ready(wr_ready),.wr_addr(wr_addr),.wr_data(wr_data),
 .ack_valid(ack_valid),.ack_ready(ack_ready),.wr_owner(wr_owner),.ack_owner(ack_owner),.ack_slot(ack_slot),.ack_identity_fault(ack_identity_fault));
 end else begin:disabled
 assign rd_ready=0;assign rsp_valid=0;assign rsp_a=0;assign rsp_b=0;
 assign wr_ready=0;assign ack_valid=0;assign ack_owner=0;assign ack_slot=0;assign ack_identity_fault=0;
 end endgenerate
endmodule
