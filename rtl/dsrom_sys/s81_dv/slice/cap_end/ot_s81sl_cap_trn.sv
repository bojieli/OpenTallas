`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81/PORTFIX-DEAD D-CAPEND (2026-10-25): capture TREE leaves of a slice-row END, where fewer than 4 frames of a column
// return rows.  The as-built die tied the missing lanes of ot_s81sl_cap_tr (rt[70 l +: 70] = 0); here those lanes do not
// exist (OWNER DECISION 8: dead ports dropped on both ends):
//   ot_s81sl_cap_tr3  lanes 0..2 (rt 210 b): na = (0, 1) full node, nb = lane 2 alone -> ot_s81_retn_fwd, nc = (na, nb)
//   ot_s81sl_cap_tr2  lanes 0..1 (rt 140 b): na = (0, 1) full node, nc = na alone -> ot_s81_retn_fwd
// Every edge and bit equal to ot_s81sl_cap_tr with the dropped lanes 0 (a one-sided node = the full node with an idle side,
// tools/s81_slice/cap_end/fwd_eq.sh; the whole leaf: tools/s81_slice/cap_end/cap_end_eq.sh), so the compiler's capture
// calendar (tools/s81_slice/cap_model.py) is unchanged.  Same reset relay (4 regions), same lane pin flops (valid bits
// reset), same sticky fault over the lanes / nodes that exist.  The CLOSED ot_s81sl_cap_tr (s81sl_cap_tr) is not edited.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap_trn #(
    parameter integer NL = 3,            // lanes 2 or 3
    parameter integer WIN = 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [70*NL-1:0]  rt,
    output wire              o_v,
    output wire [31:0]       o_t,
    output wire [31:0]       o_d,
    output wire              o_e,
    output reg               fault
);
    integer i;
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    // lane pin flops: only the valid bits are reset flops
    reg [70*NL-1:0] rt_q; reg [NL-1:0] rv_q;
    always @(posedge clk or negedge rsv[0]) if (!rsv[0]) rv_q <= '0;
        else for (i = 0; i < NL; i = i + 1) rv_q[i] <= rt[70 * i + 1] && rt[70 * i];
    always @(posedge clk) rt_q <= rt;
    wire [NL-1:0] l_v, l_e, l_f; wire [31:0] l_t [0:NL-1], l_d [0:NL-1];
    genvar gl;
    generate for (gl = 0; gl < NL; gl = gl + 1) begin : g_lane
        wire [69:0] w = rt_q[70 * gl +: 70];
        assign l_v[gl] = rv_q[gl];
        assign l_t[gl] = w[34:3];  assign l_d[gl] = w[66:35];
        assign l_e[gl] = w[67];
        assign l_f[gl] = w[69];
    end endgenerate
    wire na_v, na_e, na_f, nb_v, nb_e, nc_f; wire [31:0] na_t, na_d, nb_t, nb_d;
    ot_s81_retn_static #(.WIN(WIN), .RST(1), .DLR(1)) u_na (.clk(clk), .rst_n(rsv[1]),
        .a_v(l_v[0]), .a_t(l_t[0]), .a_d(l_d[0]), .a_e(l_e[0]),
        .b_v(l_v[1]), .b_t(l_t[1]), .b_d(l_d[1]), .b_e(l_e[1]),
        .o_v(na_v), .o_t(na_t), .o_d(na_d), .o_e(na_e), .fault(na_f));
    generate if (NL == 3) begin : g_tr3
        ot_s81_retn_fwd #(.WIN(WIN), .RST(1)) u_nb (.clk(clk), .rst_n(rsv[2]),
            .a_v(l_v[2]), .a_t(l_t[2]), .a_d(l_d[2]), .a_e(l_e[2]), .o_v(nb_v), .o_t(nb_t), .o_d(nb_d), .o_e(nb_e));
        ot_s81_retn_static #(.WIN(WIN), .RST(1), .DLR(1)) u_nc (.clk(clk), .rst_n(rsv[3]),
            .a_v(na_v), .a_t(na_t), .a_d(na_d), .a_e(na_e),
            .b_v(nb_v), .b_t(nb_t), .b_d(nb_d), .b_e(nb_e),
            .o_v(o_v), .o_t(o_t), .o_d(o_d), .o_e(o_e), .fault(nc_f));
    end else begin : g_tr2
        ot_s81_retn_fwd #(.WIN(WIN), .RST(1)) u_nc (.clk(clk), .rst_n(rsv[3]),
            .a_v(na_v), .a_t(na_t), .a_d(na_d), .a_e(na_e), .o_v(o_v), .o_t(o_t), .o_d(o_d), .o_e(o_e));
        assign nc_f = 1'b0;   // a one-sided node has no compiler obligation (no fault source)
    end endgenerate
    always @(posedge clk or negedge rsv[0])
        if (!rsv[0]) fault <= 1'b0;
        else if (na_f || nc_f || (|(l_v & l_e)) || (|l_f)) fault <= 1'b1;
`ifndef SYNTHESIS
    initial if (NL != 2 && NL != 3) $fatal(1, "ot_s81sl_cap_trn: NL 2 or 3 (4 = ot_s81sl_cap_tr)");
`endif
endmodule

// parameter-free hard-view tops (a hard view carries no parameters)
module ot_s81sl_cap_tr3 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [209:0]  rt,           // lanes 0..2
    output wire          o_v,
    output wire [31:0]   o_t,
    output wire [31:0]   o_d,
    output wire          o_e,
    output wire          fault
);
    ot_s81sl_cap_trn #(.NL(3)) u (.clk(clk), .rst_n(rst_n), .rt(rt), .o_v(o_v), .o_t(o_t), .o_d(o_d), .o_e(o_e), .fault(fault));
endmodule

module ot_s81sl_cap_tr2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [139:0]  rt,           // lanes 0..1
    output wire          o_v,
    output wire [31:0]   o_t,
    output wire [31:0]   o_d,
    output wire          o_e,
    output wire          fault
);
    ot_s81sl_cap_trn #(.NL(2)) u (.clk(clk), .rst_n(rst_n), .rt(rt), .o_v(o_v), .o_t(o_t), .o_d(o_d), .o_e(o_e), .fault(fault));
endmodule
`default_nettype wire
