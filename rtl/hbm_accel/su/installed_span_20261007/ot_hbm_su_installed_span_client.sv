`timescale 1ns/1ps
// Default-off one-outstanding installed result-span reader. No second store.
// Publication and returned owner identity must come from the real protected
// service association, not a constant echo of this descriptor. Model6ca8db61b.
module ot_hbm_su_installed_span_client #(parameter integer ENABLE=0)(
 input wire clk,por_n,warm_reset,transport_fault,
 input wire bind_v,output wire bind_r,input wire [1:0] installed_checked,
 input wire [72:0] bind_owner,input wire [15:0] bind_record,bind_tag,
 input wire [4:0] bind_source,input wire [23:0] logical_base,
 input wire [12:0] rows,input wire [36:0] byte_base,byte_limit,
 input wire publication_v,output wire publication_r,input wire [72:0] publication_owner,
 input wire [15:0] publication_record,input wire [4:0] publication_source,
 input wire read_v,output wire read_r,input wire [23:0] read_word,input wire [12:0] read_consumer,
 output wire c_req_v,input wire c_req_r,output wire c_req_we,
 output wire [36:0] c_req_addr,output wire [255:0] c_req_data,output wire [15:0] c_req_tag,output wire [93:0] c_req_context,
 input wire c_rsp_v,output wire c_rsp_r,input wire c_rsp_we,c_rsp_error,
 input wire c_rsp_identity_checked,c_rsp_context_checked,
 input wire [255:0] c_rsp_data,input wire [15:0] c_rsp_tag,input wire [93:0] c_rsp_context,
 output wire result_v,input wire result_r,output wire [31:0] result_data,output wire [12:0] result_consumer,
 input wire release_v,output wire release_r,input wire [72:0] release_owner,
 input wire [15:0] release_record,input wire [4:0] release_source,
 output wire retained,fault
);
 // Client4 of the SAME five-client ot_hbm_sm_shared_service_join. These two
 // qualifier inputs must be actual checked identity/context outputs, not ties.
 wire [72:0] req_owner;wire [15:0] req_record;wire [4:0] req_source;
 assign c_req_we=1'b0;assign c_req_data=256'b0;
 assign c_req_context={req_owner,req_record,req_source};
 ot_hbm_su_installed_span #(.ENABLE(ENABLE)) endpoint(
  .req_v(c_req_v),.req_r(c_req_r),.req_addr(c_req_addr),.req_tag(c_req_tag),
  .rsp_v(c_rsp_v),.rsp_r(c_rsp_r),.rsp_we(c_rsp_we),.rsp_error(c_rsp_error),
  .rsp_checked({c_rsp_context_checked,c_rsp_identity_checked}),
  .rsp_data(c_rsp_data),.rsp_tag(c_rsp_tag),.rsp_owner(c_rsp_context[93:21]),
  .rsp_record(c_rsp_context[20:5]),.rsp_source(c_rsp_context[4:0]),.*);
endmodule
