`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81U-CAP2 (2026-10-17): ot_s81sl_cap_tr = the TREE leaf of the capture root ot_s81sl_cap (hardened leaf, own clock root;
// ONE master, two instances: u_tw on the W frame column = lanes 0..3, u_te on the E column = lanes 4..7, placed MY).
//
// Why a leaf: the flat ot_s81sl_cap had 22,261 sinks on one root and a measured TT insertion of 368.5 ps > 300 (clock
// rule, physical/ref_tile/s81sl_cap/gate_result.json).  The cap is now three hardened leaves -- 2 x this tree leaf and
// the root leaf ot_s81sl_cap_rt -- joined by abutted wires only (ot_s81sl_cap = instances + wiring, no logic).
//
// Content = the per-column half of the old flat tree, unchanged edge for edge:
//   4 lane pin flops (rt[70 l +: 70], bit order as ot_s81sl_cap's header: rt[0] rst_n, rt[1] valid, rt[34:3] tag,
//   rt[66:35] FP32 data, rt[67] err, rt[69] fault), 3 x ot_s81_retn_static (WIN 2, RST 1): na = lanes (0,1),
//   nb = lanes (2,3), nc = (na, nb) -- the old n0/n1/n4 (W) or n2/n3/n5 (E).
// The output word o_* is nc's RST output flop and lands, at the root leaf, directly in n6's P1 port flop: the seam is
// registered on both sides and adds NO edge (the cycle model tools/s81_slice/cap_model.py is unchanged).
// fault: sticky (lane err/fault bits as old F10, node F1..F4), a flop; the root re-registers it.
// DLR (S81U-CAP4): the 3 nodes run their AL-deep side-band lanes as register-file delay lines (ot_hdc_delay_rf, cycle-exact,
// same flops) -- route 9df7f8153 FF hold -6.37 ps was all flop -> INV -> flop pass hops, half of them in those lanes.
// MUT (bench mutants only): 2 ri bit order t <-> d; 4 drops local lane 1's 3rd word (the old lane 5: E instance only).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap_tr #(
    parameter integer WIN = 2,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [279:0]  rt,           // 4 lanes x 70 (the frame cfifo rd words of one frame column)
    output wire          o_v,
    output wire [31:0]   o_t,
    output wire [31:0]   o_d,
    output wire          o_e,
    output reg           fault
);
    integer i;
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));

    // lane pin flops: only the valid bits are reset flops
    reg [279:0] rt_q; reg [3:0] rv_q;
    always @(posedge clk or negedge rsv[0]) if (!rsv[0]) rv_q <= 4'd0;
        else for (i = 0; i < 4; i = i + 1) rv_q[i] <= rt[70 * i + 1] && rt[70 * i];
    always @(posedge clk) rt_q <= rt;
    wire [3:0] l_v, l_e, l_f; wire [31:0] l_t [0:3], l_d [0:3];
    wire [3:0] drop;
    genvar gl;
    generate
        if (MUT == 4) begin : g_m4
            reg [2:0] l1_cnt;
            always @(posedge clk or negedge rsv[0]) if (!rsv[0]) l1_cnt <= 3'd0;
                                                   else if (rv_q[1] && l1_cnt != 3'd7) l1_cnt <= l1_cnt + 3'd1;
            assign drop = {2'b00, l1_cnt == 3'd2, 1'b0};
        end else begin : g_nm
            assign drop = 4'd0;
        end
        for (gl = 0; gl < 4; gl = gl + 1) begin : g_lane
            wire [69:0] w = rt_q[70 * gl +: 70];
            assign l_v[gl] = rv_q[gl] && !drop[gl];
            if (MUT == 2) begin : g_swap
                assign l_t[gl] = w[66:35]; assign l_d[gl] = w[34:3];
            end else begin : g_ok
                assign l_t[gl] = w[34:3];  assign l_d[gl] = w[66:35];
            end
            assign l_e[gl] = w[67];
            assign l_f[gl] = w[69];
        end
    endgenerate

    wire [2:0] n_v, n_e, n_f; wire [31:0] n_t [0:2], n_d [0:2];
    generate for (gl = 0; gl < 2; gl = gl + 1) begin : g_l1
        ot_s81_retn_static #(.WIN(WIN), .RST(1), .DLR(1)) u_n (.clk(clk), .rst_n(rsv[1 + gl]),
            .a_v(l_v[2*gl]), .a_t(l_t[2*gl]), .a_d(l_d[2*gl]), .a_e(l_e[2*gl]),
            .b_v(l_v[2*gl+1]), .b_t(l_t[2*gl+1]), .b_d(l_d[2*gl+1]), .b_e(l_e[2*gl+1]),
            .o_v(n_v[gl]), .o_t(n_t[gl]), .o_d(n_d[gl]), .o_e(n_e[gl]), .fault(n_f[gl]));
    end endgenerate
    ot_s81_retn_static #(.WIN(WIN), .RST(1), .DLR(1)) u_nc (.clk(clk), .rst_n(rsv[3]),
        .a_v(n_v[0]), .a_t(n_t[0]), .a_d(n_d[0]), .a_e(n_e[0]),
        .b_v(n_v[1]), .b_t(n_t[1]), .b_d(n_d[1]), .b_e(n_e[1]),
        .o_v(o_v), .o_t(o_t), .o_d(o_d), .o_e(o_e), .fault(n_f[2]));

    always @(posedge clk or negedge rsv[0])
        if (!rsv[0]) fault <= 1'b0;
        else if ((|n_f) || (|(l_v & l_e)) || (|l_f)) fault <= 1'b1;
endmodule
`default_nettype wire
