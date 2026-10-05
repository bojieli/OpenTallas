`timescale 1ns/1ps
// Own opt2 caller only. Requires Euclid owned optional PACK_W2 hook.
module ot_hbm_accel_w2_caller #(
    parameter integer ENABLE = 0, PQ_ENABLE = 0,
    parameter integer PACK_W2 = 0,       // Erdos finite FP4 pair address hook
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
                                        // stage (ot_hbm_accel_tc16, bit-identical, 0 cycles); 0 = ot_gpu_tc16;
                                        // likewise the block-dot column with the FP4 decode in its input register
                                        // (ot_hbm_accel_bd_col / ot_hbm_accel_bterm2); 0 = ot_gpu_bd_col
    parameter integer DS   = 3,         // per-sub distribution stages between s1 and the sub-half copy
    parameter integer DW   = 4,         // per-sub x-write stages between the pin register and the sub-half copy
    parameter integer DG   = 3,         // gather stages between a leaf's G1 and its column's tree input
    parameter integer PIO  = 2,         // boundary stages between the pins and the hub, each way
    parameter integer HAZ  = 1,         // PQ: retire-order hazard check (0 = negative test only)
    parameter integer NOUT = 4,         // PQ: outstanding ops in the issue
    parameter integer G1ASB = 0         // PQ negative test only: 1 = the as-built leaf G1 select (by entering format)
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    output wire                    start_ready,   // PQ
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,
    input  wire [7:0]              op_g,
    input  wire                    op_gs,
    input  wire [1:0]              op_fmt,
    input  wire                    op_pack_w2,    // same posted op tuple, not source ownership
    input  wire [6:0]              op_pack_delta_x,
    input  wire [$clog2(XD)-1:0]   op_xb,         // PQ: x-store base of the op
    output wire                    busy,
    input  wire                    d_valid,
    output wire                    d_ready,
    input  wire [31:0]             d_base,
    input  wire [23:0]             d_lines,
    output wire                    req_v,
    input  wire                    req_ready,
    output wire [31:0]             req_addr,
    output wire [9:0]              req_tag,
    input  wire                    rsp_v,
    input  wire [9:0]              rsp_tag,
    input  wire [1087:0]           rsp_data,
    input  wire                    xw_en,
    input  wire [$clog2(XD)-1:0]   xw_addr,
    input  wire [6:0]              xw_grp,
    input  wire [8*256-1:0]        xw_data,
    output wire                    rv,
    output wire [$clog2(RMAX)-1:0] rrow,
    output wire [NC*32-1:0]        rdata,
    output wire                    fault,
    output wire                    arrive,
    input  wire                    release_in,
    output wire                    released,
    input wire op_bound,
    input wire [31:0] op_id_a, op_id_b,
    input wire d_pair, d_bound,
    input wire [31:0] d_base_b,
    output wire [31:0] rop
);
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
