`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT LH-P3UNITS/UNIONTILE 10-19: per-quadrant union dispatch tile = ot_hnx_union_qdisp (dispatcher copy +
// 1 metadata macro) + ot_hnx_union_kstore (7 kernel-store macros), placed beside the quadrant calendar.
// Every input is captured in a pin register (s_in: the landed head stream word; bw_*: boot / config bus); every
// output is a flop Q (launch_* and status from the dispatcher, kw_* from the kernel-store output register, fault from
// its own register).  rst_n lands in 2 registered stages (async assert, synchronous release) before any load.
// Boot bus: bw_addr[13] = 1 -> kernel-store word bw_addr[12:0]; 0 -> dispatcher cfg bw_addr[5:0] = bw_data[31:0].
module ot_hnx_union_qtile #(
    parameter integer MUT = 0,
    parameter integer KMUT = 0
)(
    input  wire          clk,
    input  wire          rst_n,
    input  wire [49:0]   s_in,
    input  wire          bw_v,
    input  wire [13:0]   bw_addr,
    input  wire [255:0]  bw_data,
    output wire          busy,
    output reg           fault,
    output wire          abort,
    output wire          done,
    output wire          launch_v,
    output wire [1:0]    launch_loop,
    output wire [6:0]    launch_slot,
    output wire [4:0]    launch_c,
    output wire [11:0]   launch_kref,
    output wire          kw_v,
    output wire          kw_first,
    output wire          kw_half,
    output wire [255:0]  kw_data
);
    // ---------------------------------------------------------------- reset landing (2 registered stages)
    reg rst_q1, rst_q2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rst_q1 <= 1'b0; rst_q2 <= 1'b0; end
        else begin rst_q1 <= 1'b1; rst_q2 <= rst_q1; end
    wire rst_l = rst_q2;
    // ---------------------------------------------------------------- pin registers
    reg [4:0] s_cq;                   // valids: go, tv, td, uv, ufault (reset)
    reg [44:0] s_dq;                  // fields (no reset)
    reg bw_vq; reg [13:0] bw_aq; reg [255:0] bw_dq;
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin s_cq <= 5'd0; bw_vq <= 1'b0; end
        else begin s_cq <= {s_in[49], s_in[38], s_in[23], s_in[22], s_in[0]}; bw_vq <= bw_v; end
    always @(posedge clk) begin
        s_dq <= {s_in[48:39], s_in[37:24], s_in[21:1]};
        bw_aq <= bw_addr; bw_dq <= bw_data;
    end
    wire [49:0] s_q = {s_cq[4], s_dq[44:35], s_cq[3], s_dq[34:21], s_cq[2], s_cq[1], s_dq[20:0], s_cq[0]};
    // ---------------------------------------------------------------- dispatcher copy + kernel store
    wire qd_fault, kfault;
    ot_hnx_union_qdisp #(.MUT(MUT)) u_qd (
        .clk(clk), .rst_n(rst_l), .cfg_we(bw_vq && !bw_aq[13]), .cfg_addr(bw_aq[5:0]), .cfg_data(bw_dq[31:0]),
        .s(s_q), .busy(busy), .fault(qd_fault), .abort(abort), .done(done), .launch_v(launch_v),
        .launch_loop(launch_loop), .launch_slot(launch_slot), .launch_c(launch_c), .launch_kref(launch_kref));
    ot_hnx_union_kstore #(.KMUT(KMUT)) u_ks (
        .clk(clk), .rst_n(rst_l), .bw_v(bw_vq && bw_aq[13]), .bw_addr(bw_aq[12:0]), .bw_data(bw_dq),
        .l_v(launch_v), .l_loop(launch_loop), .l_kref(launch_kref),
        .kw_v(kw_v), .kw_first(kw_first), .kw_half(kw_half), .kw_data(kw_data), .kfault(kfault));
    always @(posedge clk or negedge rst_l)
        if (!rst_l) fault <= 1'b0; else fault <= qd_fault | kfault;
endmodule
`default_nettype wire
