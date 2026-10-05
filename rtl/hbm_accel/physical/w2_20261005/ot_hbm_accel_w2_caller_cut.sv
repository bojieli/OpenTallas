// Source-bound sizing cut of Erdos's actual W2 caller joins and address hook.
// No invented producer, sink, ready, clock or capture flops. Exposed borrowed
// signals are actual caller/SM boundaries and REQUIRE contextual binding before
// STA/P&R. This module is not a functional replacement for the enclosing caller.
module ot_hbm_accel_w2_caller_cut #(
    parameter integer PACK_W2=0
)(
    input wire clk,rst_n,
    input wire start,sm_ready,
    output wire start_ready,
    input wire op_pack_w2,op_bound,
    input wire [12:0] op_rows,
    input wire [31:0] op_id_a,op_id_b,
    input wire d_valid,d_pair,d_bound,
    input wire [31:0] d_base_a,d_base_b,
    input wire [23:0] d_lines,
    output wire d_ready,bc_d_valid,
    input wire bc_d_ready,
    output wire [31:0] bc_d_base,
    output wire [23:0] bc_d_lines,
    input wire bc_req_v,
    input wire [31:0] bc_req_addr,
    input wire [9:0] bc_req_tag,
    output wire bc_req_ready,req_v,
    input wire req_ready,
    output wire [31:0] req_addr,
    output wire [9:0] req_tag,
    input wire sm_rv,
    input wire [11:0] sm_row,
    input wire [255:0] sm_rdata,
    output wire rv,
    output wire [11:0] rrow,
    output wire [31:0] rop,
    output wire [255:0] rdata,
    output wire pair_complete,
    input wire pair_active,pair_shape_bound,issue_v,issue_row_ok,
    input wire [6:0] pair_delta,absolute_xa,
    input wire [12:0] virtual_row,
    output wire [6:0] selected_xa,
    output wire request_fault,result_fault,address_fault
);
    wire ctx_ready;
    assign start_ready=sm_ready && ctx_ready;
    assign rdata=sm_rdata; // the actual caller has no payload storage here
    ot_hbm_accel_w2_pair_request_join #(.ENABLE(PACK_W2),.DQ(4)) u_requests (
        .clk(clk),.rst_n(rst_n),.d_valid(d_valid),.d_ready(d_ready),
        .d_pair(d_pair),.d_bound(d_bound),.d_base_a(d_base_a),.d_base_b(d_base_b),.d_lines(d_lines),
        .bc_d_valid(bc_d_valid),.bc_d_ready(bc_d_ready),.bc_d_base(bc_d_base),.bc_d_lines(bc_d_lines),
        .bc_req_v(bc_req_v),.bc_req_ready(bc_req_ready),.bc_req_addr(bc_req_addr),.bc_req_tag(bc_req_tag),
        .req_v(req_v),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),.fault(request_fault));
    ot_hbm_accel_w2_result_join #(.ENABLE(PACK_W2),.RW(12),.NCTX(11)) u_results (
        .clk(clk),.rst_n(rst_n),.ctx_valid(start && sm_ready),.ctx_ready(ctx_ready),
        .ctx_pair(op_pack_w2),.ctx_bound(op_bound),.ctx_rows(op_rows),
        .ctx_op_a(op_id_a),.ctx_op_b(op_id_b),.rsp_v(sm_rv),.rsp_row(sm_row),
        .out_v(rv),.out_row(rrow),.out_operation(rop),.pair_complete(pair_complete),.fault(result_fault));
    ot_hbm_accel_w2_address_hook #(.ENABLE(PACK_W2),.RW(12)) u_address (
        .pair_active(pair_active),.pair_shape_bound(pair_shape_bound),.pair_delta(pair_delta),
        .issue_v(issue_v),.issue_row_ok(issue_row_ok),.virtual_row(virtual_row),
        .absolute_xa(absolute_xa),.selected_xa(selected_xa),.fault(address_fault));
endmodule
