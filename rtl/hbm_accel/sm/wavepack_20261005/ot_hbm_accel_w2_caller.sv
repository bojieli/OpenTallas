`timescale 1ns/1ps
// Own opt2 caller only. Requires Euclid owned optional PACK_W2 hook.
module ot_hbm_accel_w2_caller #(
    parameter integer ENABLE = 0, PQ_ENABLE = 0,
    parameter integer PACK_W2 = 0,
    parameter integer XMAP = 0,         // Pauli static layout; original leaf remains selected by default
    parameter integer SUB  = 4,
    parameter integer LBS  = 2,
    parameter integer LSB  = 16,
    parameter integer NC   = 8,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer LEV  = 4,
    parameter integer XD   = 128,
    parameter integer MAX_OUT = 512,
    parameter integer TCK  = 1,         // ENABLE = 1: BF16 column with the bubble gate off the multiplier's first
                                        // stage (ot_hbm_accel_tc16, bit-identical, 0 cycles);

    localparam integer RW=$clog2(RMAX);
    wire sm_ready,ctx_ready,sm_rv,sm_fault,req_fault,ctx_fault;
    wire [RW-1:0] sm_row;
    wire bc_d_v,bc_d_r,bc_req_v,bc_req_r;
    wire [31:0] bc_d_base,bc_req_addr;
    wire [23:0] bc_d_lines;
    wire [9:0] bc_req_tag;
    assign start_ready=sm_ready && ctx_ready;
    ot_hbm_accel_w2_pair_request_join #(.ENABLE(PACK_W2)) u_requests (
        .clk(clk),.rst_n(rst_n),.d_valid(d_valid),.d_ready(d_ready),
        .d_pair(d_pair),.d_bound(d_bound),.d_base_a(d_base),.d_base_b(d_base_b),.d_lines(d_lines),
        .bc_d_valid(bc_d_v),.bc_d_ready(bc_d_r),.bc_d_base(bc_d_base),.bc_d_lines(bc_d_lines),
        .bc_req_v(bc_req_v),.bc_req_ready(bc_req_r),.bc_req_addr(bc_req_addr),.bc_req_tag(bc_req_tag),
        .req_v(req_v),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),.fault(req_fault));
    ot_hbm_accel_w2_result_join #(.ENABLE(PACK_W2),.RW(RW)) u_results (
        .clk(clk),.rst_n(rst_n),.ctx_valid(start && sm_ready),.ctx_ready(ctx_ready),
        .ctx_pair(op_pack_w2),.ctx_bound(op_bound),.ctx_rows(op_rows),
        .ctx_op_a(op_id_a),.ctx_op_b(op_id_b),.rsp_v(sm_rv),.rsp_row(sm_row),
        .out_v(rv),.out_row(rrow),.out_operation(rop),.pair_complete(),.fault(ctx_fault));
    ot_hbm_accel_sm_pq #(.ENABLE(ENABLE),.PQ_ENABLE(PQ_ENABLE),.PACK_W2(PACK_W2),.XMAP(XMAP),
        .SUB(SUB),.LBS(LBS),.LSB(LSB),.NC(NC),.IL(IL),.RMAX(RMAX),.LEV(LEV),.XD(XD),
        .MAX_OUT(MAX_OUT),.TCK(TCK),.DS(DS),.DW(DW),.DG(DG),.PIO(PIO),.HAZ(HAZ),.NOUT(NOUT),.G1ASB(G1ASB)) u_sm (
        .clk(clk),.rst_n(rst_n),.start(start && ctx_ready),.start_ready(sm_ready),
        .op_rows(op_rows),.op_c(op_c),.op_g(op_g),.op_gs(op_gs),.op_fmt(op_fmt),.op_xb(op_xb),
        .op_pack_w2(op_pack_w2),.op_pack_delta_x(op_pack_delta_x),
        .busy(busy),.d_valid(bc_d_v),.d_ready(bc_d_r),.d_base(bc_d_base),.d_lines(bc_d_lines),
        .req_v(bc_req_v),.req_ready(bc_req_r),.req_addr(bc_req_addr),.req_tag(bc_req_tag),
        .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
        .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
        .rv(sm_rv),.rrow(sm_row),.rdata(rdata),.fault(sm_fault),.arrive(arrive),
        .release_in(release_in),.released(released));
    assign fault=sm_fault|req_fault|ctx_fault;
endmodule
