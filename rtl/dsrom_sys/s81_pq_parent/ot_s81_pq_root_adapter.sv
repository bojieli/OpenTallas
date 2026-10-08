`timescale 1ns/1ps
// Candidate parent ABI adapter, off the selected die path. The 66-bit input is
// exactly dsfd_node/dsfd_rstg {error,data,tag,valid}. Instantiate the real native
// final reduction/rounding owner; this is not a combinational cast to69 bits.
// ROOTD128 matches ot_v41_field_pq_w17w10. No ready exists: the source schedule
// must bound occupancy; native overflow and upstream fault remain visible.
module ot_s81_pq_root_adapter #(
    parameter integer R = 128,
    parameter integer ROOTD = 128,
    parameter bit PIPELINED_CAM = 0
) (
    input wire clk,
    input wire rst_n,
    input wire [66*R-1:0] tree_return,
    input wire [R-1:0] upstream_fault,
    output wire [R-1:0] r_v,
    output wire [16*R-1:0] r_row,
    output wire [3*R-1:0] r_pos,
    output wire [32*R-1:0] r_fp32,
    output wire [16*R-1:0] r_bf16,
    output wire [R-1:0] r_e,
    output wire [R-1:0] root_fault
);
    genvar r;
    generate for (r=0; r<R; r=r+1) begin: g_root
        wire fault;
        if (PIPELINED_CAM) begin: g_cam
        ot_s81_pq_ret_root_cam #(.D(ROOTD),.QD(ROOTD)) u_root (
            .clk(clk),.rst_n(rst_n),
            .i_v(tree_return[66*r]),.i_t(tree_return[66*r+1 +: 32]),
            .i_d(tree_return[66*r+33 +: 32]),.i_e(tree_return[66*r+65]),.i_p(1'b0),.up_fault(1'b0),
            .r_v(r_v[r]),.r_row(r_row[16*r +: 16]),.r_pos(r_pos[3*r +: 3]),
            .r_fp32(r_fp32[32*r +: 32]),.r_bf16(r_bf16[16*r +: 16]),
            .r_e(r_e[r]),.r_p(),.fault(fault));
        end else begin: g_native
        ot_v41_ret_root #(.D(ROOTD),.QD(ROOTD)) u_root (
            .clk(clk),.rst_n(rst_n),
            .i_v(tree_return[66*r]),.i_t(tree_return[66*r+1 +: 32]),
            .i_d(tree_return[66*r+33 +: 32]),.i_e(tree_return[66*r+65]),
            .r_v(r_v[r]),.r_row(r_row[16*r +: 16]),.r_pos(r_pos[3*r +: 3]),
            .r_fp32(r_fp32[32*r +: 32]),.r_bf16(r_bf16[16*r +: 16]),
            .r_e(r_e[r]),.fault(fault));
        end
        assign root_fault[r] = fault | upstream_fault[r];
    end endgenerate
endmodule
